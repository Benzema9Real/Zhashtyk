from django.contrib.auth import logout
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import LoginSerializer, PasswordResetRequestSerializer, \
    PasswordResetConfirmationSerializer, PasswordResetCodeSerializer
from .models import PasswordResetCode
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
import random
from .models import Profile
from .serializers import RegisterSerializer, UserSerializer
from django.utils import timezone
from rest_framework.authtoken.models import Token


class RegisterView(generics.CreateAPIView):
    queryset = Profile.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        return Response({
            "token": token,
            "user_id": user.id,
            "email": user.email,
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            refresh = RefreshToken.for_user(user)
            token = str(refresh.access_token)

            user_data = UserSerializer(user).data

            data = {
                "token": token,
                "user": user_data,
                "message": "User logged in successfully."
            }
            return Response(data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        try:
            reset_code = PasswordResetCode.objects.filter(user_reset=user).latest('created_at_reset')  # Исправлено
            if not reset_code.can_resend():
                return Response({"message": "Вы можете запросить новый код через 24 часа."},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
        except PasswordResetCode.DoesNotExist:
            reset_code = None

        # Генерация кода для сброса пароля
        code_reset = str(random.randint(100000, 999999))

        # Сохраняем код в базу данных
        PasswordResetCode.objects.create(
            user_reset=user,
            code_reset=code_reset,
            last_sent=timezone.now()
        )

        # Отправляем код на email пользователя
        send_mail(
            'Password Reset Code',
            f'Your password reset code: {code_reset}',
            'sendemail@fund4.pro',  # Ваш email
            [user.email],
            fail_silently=False,
        )

        return Response({"message": "Код для восстановления пароля отправлен на ваш email"}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetCodeSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code_reset = serializer.validated_data['code']

        # Проверяем, существует ли код сброса и валиден ли он
        try:
            reset_code = PasswordResetCode.objects.get(code_reset=code_reset)
            reset_code.confirmed = True  # Устанавливаем флаг подтверждения
            reset_code.save()
        except PasswordResetCode.DoesNotExist:
            return Response({"message": "Неверный код восстановления"}, status=status.HTTP_400_BAD_REQUEST)

        # Код подтверждён, пользователь может теперь установить новый пароль
        return Response({"message": "Код подтверждён. Установите новый пароль."}, status=status.HTTP_200_OK)


class PasswordSetNewView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Получаем код сброса
        reset_code = PasswordResetCode.objects.get(confirmed=True)

        # Проверяем, был ли код подтвержден
        if not reset_code.confirmed:
            return Response({"message": "Код не подтверждён."}, status=400)

        # Обновляем пароль пользователя
        user = reset_code.user_reset
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Удаляем использованный код сброса
        if reset_code.can_delete():  # Метод can_reset() должен быть реализован в вашей модели
            # Удаляем использованный код сброса
            reset_code.delete()

        return Response({"message": "Пароль успешно изменён"}, status=200)


class LogoutView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass

        logout(request)

        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
