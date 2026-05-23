import pytest

from apps.users.repositories import UserRepository

from .factories import UserFactory


@pytest.mark.django_db
class TestUserRepository:
    def setup_method(self):
        self.repo = UserRepository()

    def test_create_user(self):
        user = self.repo.create(
            email="repo@example.com",
            username="repouser",
            password="strongpass123",
        )
        assert user.pk is not None
        assert user.email == "repo@example.com"

    def test_get_by_id(self):
        user = UserFactory()
        found = self.repo.get_by_id(user.pk)
        assert found is not None
        assert found.pk == user.pk

    def test_get_by_id_returns_none_for_missing(self):
        assert self.repo.get_by_id(99999) is None

    def test_get_by_email(self):
        user = UserFactory(email="findme@example.com")
        found = self.repo.get_by_email("findme@example.com")
        assert found is not None
        assert found.pk == user.pk

    def test_get_by_email_returns_none_for_missing(self):
        assert self.repo.get_by_email("notexist@example.com") is None

    def test_exists_by_email_true(self):
        UserFactory(email="exists@example.com")
        assert self.repo.exists_by_email("exists@example.com") is True

    def test_exists_by_email_false(self):
        assert self.repo.exists_by_email("nothere@example.com") is False

    def test_update_user(self):
        user = UserFactory(notification_sms=False)
        updated = self.repo.update(user, notification_sms=True)
        updated.refresh_from_db()
        assert updated.notification_sms is True

    def test_delete_user(self):
        user = UserFactory()
        pk = user.pk
        self.repo.delete(user)
        assert self.repo.get_by_id(pk) is None
