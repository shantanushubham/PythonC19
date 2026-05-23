from decimal import Decimal

import pytest

from apps.flights.models import FlightRoute, Notification, PriceAlert, Threshold

from .factories import (
    FlightRouteFactory,
    NotificationFactory,
    PriceAlertFactory,
    ThresholdFactory,
)


@pytest.mark.django_db
class TestFlightRouteModel:
    def test_create_route(self):
        route = FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")
        assert route.pk is not None
        assert str(route) == "BOM → DEL (IndiGo)"

    def test_str_without_airline(self):
        route = FlightRouteFactory(origin="BOM", destination="DEL", airline="")
        assert str(route) == "BOM → DEL (Any)"

    def test_unique_together_constraint(self):
        FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")


@pytest.mark.django_db
class TestThresholdModel:
    def test_is_breached_at_threshold(self):
        t = ThresholdFactory(amount=Decimal("5000"))
        assert t.is_breached_by(Decimal("5000")) is True

    def test_is_breached_below_threshold(self):
        t = ThresholdFactory(amount=Decimal("5000"))
        assert t.is_breached_by(Decimal("4999")) is True

    def test_is_not_breached_above_threshold(self):
        t = ThresholdFactory(amount=Decimal("5000"))
        assert t.is_breached_by(Decimal("5001")) is False

    def test_str_representation(self):
        t = ThresholdFactory(amount=Decimal("3000"), currency="USD")
        assert str(t) == "USD 3000"


@pytest.mark.django_db
class TestPriceAlertModel:
    def test_is_active(self):
        alert = PriceAlertFactory(status=PriceAlert.Status.ACTIVE)
        assert alert.is_active is True

    def test_is_not_active_when_paused(self):
        alert = PriceAlertFactory(status=PriceAlert.Status.PAUSED)
        assert alert.is_active is False

    def test_check_price_updates_current_price(self):
        alert = PriceAlertFactory()
        price = Decimal("4500")
        alert.check_price(price)
        alert.refresh_from_db()
        assert alert.current_price == price

    def test_check_price_returns_true_when_breached(self):
        threshold = ThresholdFactory(amount=Decimal("5000"))
        alert = PriceAlertFactory(threshold=threshold)
        assert alert.check_price(Decimal("4999")) is True

    def test_check_price_returns_false_when_not_breached(self):
        threshold = ThresholdFactory(amount=Decimal("5000"))
        alert = PriceAlertFactory(threshold=threshold)
        assert alert.check_price(Decimal("5500")) is False


@pytest.mark.django_db
class TestNotificationModel:
    def test_create_notification(self):
        n = NotificationFactory()
        assert n.pk is not None
        assert n.is_read is False

    def test_str_representation(self):
        n = NotificationFactory(channel=Notification.Channel.EMAIL, status=Notification.Status.SENT)
        assert "email" in str(n)
        assert "sent" in str(n)
