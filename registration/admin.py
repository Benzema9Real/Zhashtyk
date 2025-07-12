from django.contrib import admin
from .models import Profile, PasswordResetCode

admin.site.register(Profile)
admin.site.register(PasswordResetCode)
