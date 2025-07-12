import random
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.core.validators import EmailValidator
from requests import Response
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from .models import Profile, PasswordResetCode
from django.contrib.auth import authenticate


class ProfilePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['name']
        read_only_fields = ['user']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Profile
        fields = ['name', 'email', 'password',]

    def generate_username(self):
        last_user = User.objects.order_by('id').last()
        if last_user is None:
            return 'user000001'
        last_username = last_user.username
        try:
            last_number = int(last_username[4:])
            new_number = last_number + 1
            return f'user{new_number:06d}'
        except ValueError:
            return 'user000001'

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким адресом электронной почты уже существует.")
        return value

    def create(self, validated_data):
        name = validated_data.pop('name')

        user = User.objects.create(
            username=self.generate_username(),
            email=validated_data['email'],
            password=make_password(validated_data['password']) )
        profile = Profile.objects.create(
            user=user,
            name=name,
        )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Найдите пользователя по email
        user = User.objects.filter(email=email).first()

        if user is None:
            raise serializers.ValidationError("Неверный email или пароль.")

        # Аутентификация пользователя
        user = authenticate(username=user.username, password=password)

        if user is None:
            raise serializers.ValidationError("Неверный email или пароль.")

        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким email не найден")
        return value

    def save(self):
        email = self.validated_data['email']
        return User.objects.get(email=email)


class PasswordResetCodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=6)


class PasswordResetConfirmationSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError("Пароли не совпадают")

        try:
            validate_password(new_password)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e)})

        return data
