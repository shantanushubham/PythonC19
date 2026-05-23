from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .repositories import UserRepository

User = get_user_model()


class UserService:
    """Business logic layer for user management."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        phone_number: str = "",
        notification_email: bool = True,
        notification_sms: bool = False,
    ) -> User:
        if self.repository.exists_by_email(email):
            raise ValueError(f"A user with email '{email}' already exists.")
        return self.repository.create(
            email=email,
            username=username,
            password=password,
            phone_number=phone_number,
            notification_email=notification_email,
            notification_sms=notification_sms,
        )

    def login(self, *, email: str, password: str) -> tuple:
        user = authenticate(username=email, password=password)
        if user is None:
            raise ValueError("Invalid credentials.")
        refresh = RefreshToken.for_user(user)
        tokens = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
        return user, tokens

    def get_user(self, user_id: int) -> User:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User with id={user_id} not found.")
        return user

    def update_notification_preferences(
        self,
        user: User,
        *,
        notification_email: bool | None = None,
        notification_sms: bool | None = None,
    ) -> User:
        updates = {}
        if notification_email is not None:
            updates["notification_email"] = notification_email
        if notification_sms is not None:
            updates["notification_sms"] = notification_sms
        if updates:
            self.repository.update(user, **updates)
        return user
