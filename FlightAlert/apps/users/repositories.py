from typing import Optional

from django.contrib.auth import get_user_model

User = get_user_model()


class UserRepository:
    """Data-access layer for the User model."""

    def get_by_id(self, user_id: int) -> Optional[User]:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    def create(
        self,
        *,
        email: str,
        username: str,
        password: str,
        phone_number: str = "",
        notification_email: bool = True,
        notification_sms: bool = False,
    ) -> User:
        return User.objects.create_user(
            email=email,
            username=username,
            password=password,
            phone_number=phone_number,
            notification_email=notification_email,
            notification_sms=notification_sms,
        )

    def update(self, user: User, **kwargs) -> User:
        for field, value in kwargs.items():
            setattr(user, field, value)
        user.save(update_fields=list(kwargs.keys()) + ["updated_at"])
        return user

    def delete(self, user: User) -> None:
        user.delete()

    def list_all(self):
        return User.objects.all()

    def exists_by_email(self, email: str) -> bool:
        return User.objects.filter(email=email).exists()
