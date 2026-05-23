from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "is_staff", "notification_email", "notification_sms"]
    search_fields = ["email", "username"]
    ordering = ["email"]
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "FlightAlert Settings",
            {"fields": ("phone_number", "notification_email", "notification_sms")},
        ),
    )
