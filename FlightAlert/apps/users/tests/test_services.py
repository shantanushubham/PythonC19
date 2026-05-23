import pytest

from apps.users.services import UserService

from .factories import UserFactory


@pytest.mark.django_db
class TestUserService:
    def setup_method(self):
        self.service = UserService()

    def test_register_creates_user(self):
        user = self.service.register(
            email="new@example.com",
            username="newuser",
            password="securepass1",
        )
        assert user.pk is not None
        assert user.email == "new@example.com"

    def test_register_raises_on_duplicate_email(self):
        UserFactory(email="dup@example.com")
        with pytest.raises(ValueError, match="already exists"):
            self.service.register(
                email="dup@example.com",
                username="dupuser",
                password="securepass1",
            )

    def test_login_returns_user_and_jwt_tokens(self):
        user = UserFactory(email="login@example.com")
        user.set_password("correctpass")
        user.save()

        logged_in_user, tokens = self.service.login(
            email="login@example.com", password="correctpass"
        )
        assert logged_in_user.pk == user.pk
        assert "access" in tokens
        assert "refresh" in tokens
        assert isinstance(tokens["access"], str)
        assert isinstance(tokens["refresh"], str)

    def test_login_raises_on_bad_credentials(self):
        UserFactory(email="bad@example.com")
        with pytest.raises(ValueError, match="Invalid credentials"):
            self.service.login(email="bad@example.com", password="wrongpass")

    def test_get_user_by_id(self):
        user = UserFactory()
        found = self.service.get_user(user.pk)
        assert found.pk == user.pk

    def test_get_user_raises_for_missing(self):
        with pytest.raises(ValueError, match="not found"):
            self.service.get_user(99999)

    def test_update_notification_preferences(self):
        user = UserFactory(notification_email=True, notification_sms=False)
        updated = self.service.update_notification_preferences(
            user, notification_sms=True
        )
        updated.refresh_from_db()
        assert updated.notification_sms is True
        assert updated.notification_email is True
