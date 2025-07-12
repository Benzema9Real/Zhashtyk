from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.contrib.auth.models import User
from django.db import models


class PasswordResetCode(models.Model):
    user_reset = models.ForeignKey(User, on_delete=models.CASCADE)
    code_reset = models.CharField(max_length=6)
    created_at_reset = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    confirmed = models.BooleanField(default=False)

    def can_resend(self):
        """Проверяем, прошло ли 30 минут с момента последней отправки кода."""
        if self.last_sent:
            return (timezone.now() - self.last_sent).total_seconds() >= 30 * 60
        return True

    def can_reset(self):
        """Проверяем, прошло ли 24 часа с момента последнего сброса пароля."""
        if self.created_at_reset:
            return (timezone.now() - self.created_at_reset).total_seconds() >= 24 * 60 * 60
        return True

    def can_delete(self):

        if self.created_at_reset:
            return (timezone.now() - self.created_at_reset).total_seconds() >= 25 * 60 * 60
        return True



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deals_profile')
    name = models.CharField('Ф.И.О', max_length=300)
    registration_date = models.DateTimeField('Дата регистрации', default=timezone.now)


