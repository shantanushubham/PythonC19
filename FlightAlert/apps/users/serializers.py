from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    phone_number = serializers.CharField(max_length=20, required=False, default="")
    notification_email = serializers.BooleanField(default=True)
    notification_sms = serializers.BooleanField(default=False)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "phone_number",
            "notification_email",
            "notification_sms",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationPreferenceSerializer(serializers.Serializer):
    notification_email = serializers.BooleanField(required=False)
    notification_sms = serializers.BooleanField(required=False)
