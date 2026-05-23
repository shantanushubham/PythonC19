import pytest

from .factories import UserFactory


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = UserFactory(email="test@example.com", username="testuser")
        assert user.pk is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_str_representation(self):
        user = UserFactory(email="hello@example.com")
        assert str(user) == "hello@example.com"

    def test_email_is_unique(self):
        UserFactory(email="unique@example.com")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            UserFactory(email="unique@example.com")

    def test_default_notification_preferences(self):
        user = UserFactory()
        assert user.notification_email is True
        assert user.notification_sms is False

    def test_username_field_is_email(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        assert User.USERNAME_FIELD == "email"
