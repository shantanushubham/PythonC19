from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.flights.models import Notification, PriceAlert
from apps.flights.services import FlightRouteService, NotificationService, PriceAlertService
from apps.users.tests.factories import UserFactory

from .factories import FlightRouteFactory, NotificationFactory, PriceAlertFactory, ThresholdFactory


@pytest.mark.django_db
class TestFlightRouteService:
    def setup_method(self):
        self.service = FlightRouteService()

    def test_get_or_create_new_route(self):
        route, created = self.service.get_or_create_route(
            origin="BOM", destination="DEL", airline="IndiGo"
        )
        assert created is True
        assert route.origin == "BOM"
        assert route.destination == "DEL"

    def test_get_or_create_existing_route(self):
        FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")
        route, created = self.service.get_or_create_route(
            origin="bom", destination="del", airline="IndiGo"
        )
        assert created is False

    def test_same_origin_destination_raises(self):
        with pytest.raises(ValueError, match="cannot be the same"):
            self.service.get_or_create_route(origin="BOM", destination="BOM")

    def test_get_route_raises_for_missing(self):
        with pytest.raises(ValueError, match="not found"):
            self.service.get_route(99999)

    def test_search_routes(self):
        FlightRouteFactory(origin="BLR", destination="MAA", airline="SpiceJet")
        results = list(self.service.search_routes(origin="BLR", destination="MAA"))
        assert len(results) == 1


@pytest.mark.django_db
class TestPriceAlertService:
    def setup_method(self):
        self.service = PriceAlertService()

    def test_create_alert(self):
        user = UserFactory()
        alert = self.service.create_alert(
            user=user,
            origin="BOM",
            destination="DEL",
            threshold_amount=Decimal("5000"),
        )
        assert alert.pk is not None
        assert alert.user == user
        assert alert.threshold.amount == Decimal("5000")

    def test_create_alert_same_origin_destination_raises(self):
        user = UserFactory()
        with pytest.raises(ValueError):
            self.service.create_alert(
                user=user,
                origin="BOM",
                destination="BOM",
                threshold_amount=Decimal("5000"),
            )

    def test_list_alerts_for_user(self):
        user = UserFactory()
        PriceAlertFactory(user=user)
        PriceAlertFactory(user=user)
        PriceAlertFactory()
        alerts = list(self.service.list_alerts_for_user(user))
        assert len(alerts) == 2

    def test_pause_and_resume_alert(self):
        alert = PriceAlertFactory(status=PriceAlert.Status.ACTIVE)
        self.service.pause_alert(alert)
        alert.refresh_from_db()
        assert alert.status == PriceAlert.Status.PAUSED

        self.service.resume_alert(alert)
        alert.refresh_from_db()
        assert alert.status == PriceAlert.Status.ACTIVE

    def test_delete_alert(self):
        alert = PriceAlertFactory()
        pk = alert.pk
        self.service.delete_alert(alert)
        assert PriceAlert.objects.filter(pk=pk).count() == 0

    def test_process_price_update_triggers_notification(self):
        route = FlightRouteFactory(origin="BOM", destination="DEL", airline="IndiGo")
        threshold = ThresholdFactory(amount=Decimal("5000"))
        user = UserFactory(notification_email=False, notification_sms=False)
        PriceAlertFactory(user=user, flight_route=route, threshold=threshold)

        notifications = self.service.process_price_update(
            route=route, new_price=Decimal("4500")
        )
        assert len(notifications) == 1  # IN_APP only

    def test_process_price_update_no_trigger_when_above_threshold(self):
        route = FlightRouteFactory(origin="BOM", destination="HYD", airline="IndiGo")
        threshold = ThresholdFactory(amount=Decimal("5000"))
        user = UserFactory()
        PriceAlertFactory(user=user, flight_route=route, threshold=threshold)

        notifications = self.service.process_price_update(
            route=route, new_price=Decimal("6000")
        )
        assert len(notifications) == 0

    def test_process_price_update_marks_alert_triggered(self):
        route = FlightRouteFactory(origin="AMD", destination="PNQ", airline="IndiGo")
        threshold = ThresholdFactory(amount=Decimal("3000"))
        user = UserFactory(notification_email=False, notification_sms=False)
        alert = PriceAlertFactory(user=user, flight_route=route, threshold=threshold)

        self.service.process_price_update(route=route, new_price=Decimal("2500"))
        alert.refresh_from_db()
        assert alert.status == PriceAlert.Status.TRIGGERED


@pytest.mark.django_db
class TestNotificationService:
    def setup_method(self):
        self.service = NotificationService()

    def test_send_notification_creates_in_app_by_default(self):
        user = UserFactory(notification_email=False, notification_sms=False)
        alert = PriceAlertFactory(user=user)
        notifications = self.service.send_alert_notification(
            alert=alert, triggered_price=Decimal("4500")
        )
        assert len(notifications) == 1
        assert notifications[0].channel == Notification.Channel.IN_APP

    def test_send_notification_includes_email_channel(self):
        user = UserFactory(notification_email=True, notification_sms=False)
        alert = PriceAlertFactory(user=user)
        notifications = self.service.send_alert_notification(
            alert=alert, triggered_price=Decimal("4500")
        )
        channels = {n.channel for n in notifications}
        assert Notification.Channel.EMAIL in channels
        assert Notification.Channel.IN_APP in channels

    def test_send_notification_includes_sms_when_phone_set(self):
        user = UserFactory(notification_email=False, notification_sms=True, phone_number="+919876543210")
        alert = PriceAlertFactory(user=user)
        notifications = self.service.send_alert_notification(
            alert=alert, triggered_price=Decimal("4500")
        )
        channels = {n.channel for n in notifications}
        assert Notification.Channel.SMS in channels

    def test_mark_read(self):
        n = NotificationFactory(is_read=False)
        self.service.mark_read(n)
        n.refresh_from_db()
        assert n.is_read is True

    def test_get_notification_raises_for_missing(self):
        with pytest.raises(ValueError, match="not found"):
            self.service.get_notification(99999)

    def test_message_content(self):
        user = UserFactory(notification_email=False, notification_sms=False)
        alert = PriceAlertFactory(user=user)
        alert.flight_route.origin = "BOM"
        alert.flight_route.destination = "DEL"
        alert.flight_route.save()
        alert.threshold.amount = Decimal("5000")
        alert.threshold.save()

        notifications = self.service.send_alert_notification(
            alert=alert, triggered_price=Decimal("4500")
        )
        assert "BOM" in notifications[0].message
        assert "DEL" in notifications[0].message
        assert "4500" in notifications[0].message
