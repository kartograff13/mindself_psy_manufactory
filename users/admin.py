from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = list(BaseUserAdmin.list_display) + ["role",]
    list_filter = list(BaseUserAdmin.list_filter) + ["role",]
    fieldsets = list(BaseUserAdmin.fieldsets or []) + [("Дополнительно", {"fields": ("role",)})]
