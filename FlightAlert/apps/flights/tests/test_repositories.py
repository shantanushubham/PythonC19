from decimal import Decimal

import pytest

from apps.flights.models import Notification, PriceAlert
from apps.flights.repositories import (
    FlightRouteRepository,
    NotificationRepository,
    PriceAlertRepository,
    ThresholdRepository,
)

from .factories import (
    FlightRouteFactory,
    NotificationFactory,
    PriceAlertFactory,
    ThresholdFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFlightRouteRepository:
    def setup_method(self):
        self.repo = FlightRouteRepository()

    def test_create_route(self):
        route = self.repo.create(origin="BOM", destination="DEL", airline="IndiGo")
        assert route.pk is not None
        assert route.origin == "BOM"

    def test_get_or_create_returns_existing(self):
        existing = FlightRouteFactory(origin="BLR", destination="MAA", airline="SpiceJet")
        route, created = self.repo.get_or_create(origin="BLR", destination="MAA", airline="SpiceJet")
        assert created is False
        assert route.pk == existing.pk

    def test_get_by_id(self):
        route = FlightRouteFactory()
        found = self.repo.get_by_id(route.pk)
        assert found is not None
        assert found.pk == route.pk

    def test_get_by_id_returns_none(self):
        assert self.repo.get_by_id(99999) is None

    def test_list_active(self):
        FlightRouteFactory(is_active=True)
        FlightRouteFactory(is_active=False)
        active = list(self.repo.list_active())
        assert all(r.is_active for r in active)

    def test_search(self):
        FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")
        FlightRouteFactory(origin="DEL", destination="BOM", airline="IndiGo")
        results = list(self.repo.search(origin="BOM", destination="DEL"))
        assert len(results) == 1
        assert results[0].origin == "BOM"


@pytest.mark.django_db
class TestThresholdRepository:
    def setup_method(self):
        self.repo = ThresholdRepository()

    def test_create(self):
        t = self.repo.create(amount=Decimal("3000"), currency="INR")
        assert t.pk is not None
        assert t.amount == Decimal("3000")

    def test_get_by_id(self):
        t = ThresholdFactory()
        found = self.repo.get_by_id(t.pk)
        assert found is not None

    def test_get_by_id_none(self):
        assert self.repo.get_by_id(99999) is None

    def test_update(self):
        t = ThresholdFactory(amount=Decimal("5000"), currency="INR")
        updated = self.repo.update(t, amount=Decimal("4000"), currency="USD")
        updated.refresh_from_db()
        assert updated.amount == Decimal("4000")
        assert updated.currency == "USD"


@pytest.mark.django_db
class TestPriceAlertRepository:
    def setup_method(self):
        self.repo = PriceAlertRepository()

    def test_create_alert(self):
        user = UserFactory()
        route = FlightRouteFactory()
        threshold = ThresholdFactory()
        alert = self.repo.create(user=user, flight_route=route, threshold=threshold)
        assert alert.pk is not None
        assert alert.status == PriceAlert.Status.ACTIVE

    def test_get_by_id(self):
        alert = PriceAlertFactory()
        found = self.repo.get_by_id(alert.pk)
        assert found is not None

    def test_list_for_user(self):
        user = UserFactory()
        PriceAlertFactory(user=user)
        PriceAlertFactory(user=user)
        PriceAlertFactory()
        alerts = list(self.repo.list_for_user(user))
        assert len(alerts) == 2

    def test_list_active_for_route(self):
        route = FlightRouteFactory()
        PriceAlertFactory(flight_route=route, status=PriceAlert.Status.ACTIVE)
        PriceAlertFactory(flight_route=route, status=PriceAlert.Status.PAUSED)
        active = list(self.repo.list_active_for_route(route))
        assert len(active) == 1

    def test_update_status(self):
        alert = PriceAlertFactory(status=PriceAlert.Status.ACTIVE)
        self.repo.update_status(alert, PriceAlert.Status.PAUSED)
        alert.refresh_from_db()
        assert alert.status == PriceAlert.Status.PAUSED


@pytest.mark.django_db
class TestNotificationRepository:
    def setup_method(self):
        self.repo = NotificationRepository()

    def test_create_notification(self):
        alert = PriceAlertFactory()
        n = self.repo.create(
            user=alert.user,
            price_alert=alert,
            channel=Notification.Channel.EMAIL,
            message="Price dropped!",
            triggered_price=Decimal("4800"),
        )
        assert n.pk is not None
        assert n.status == Notification.Status.PENDING

    def test_list_unread_for_user(self):
        user = UserFactory()
        alert = PriceAlertFactory(user=user)
        NotificationFactory(user=user, price_alert=alert, is_read=False)
        NotificationFactory(user=user, price_alert=alert, is_read=True)
        unread = list(self.repo.list_unread_for_user(user))
        assert len(unread) == 1
        assert unread[0].is_read is False

    def test_mark_read(self):
        n = NotificationFactory(is_read=False)
        self.repo.mark_read(n)
        n.refresh_from_db()
        assert n.is_read is True

    def test_mark_sent(self):
        n = NotificationFactory(status=Notification.Status.PENDING)
        self.repo.mark_sent(n, sent_at=None)
        n.refresh_from_db()
        assert n.status == Notification.Status.SENT
        assert n.sent_at is not None
