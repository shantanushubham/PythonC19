from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet

from .models import FlightRoute, Notification, PriceAlert, Threshold


class FlightRouteRepository:
    """Data-access layer for FlightRoute."""

    def get_by_id(self, route_id: int) -> Optional[FlightRoute]:
        try:
            return FlightRoute.objects.get(pk=route_id)
        except FlightRoute.DoesNotExist:
            return None

    def get_or_create(
        self, *, origin: str, destination: str, airline: str = ""
    ) -> tuple[FlightRoute, bool]:
        return FlightRoute.objects.get_or_create(
            origin=origin.upper(),
            destination=destination.upper(),
            airline=airline,
        )

    def list_active(self) -> QuerySet[FlightRoute]:
        return FlightRoute.objects.filter(is_active=True)

    def search(self, origin: str, destination: str) -> QuerySet[FlightRoute]:
        return FlightRoute.objects.filter(
            origin=origin.upper(),
            destination=destination.upper(),
            is_active=True,
        )

    def create(self, *, origin: str, destination: str, airline: str = "") -> FlightRoute:
        return FlightRoute.objects.create(
            origin=origin.upper(),
            destination=destination.upper(),
            airline=airline,
        )

    def delete(self, route: FlightRoute) -> None:
        route.delete()


class ThresholdRepository:
    """Data-access layer for Threshold."""

    def get_by_id(self, threshold_id: int) -> Optional[Threshold]:
        try:
            return Threshold.objects.get(pk=threshold_id)
        except Threshold.DoesNotExist:
            return None

    def create(self, *, amount: Decimal, currency: str = "INR") -> Threshold:
        return Threshold.objects.create(amount=amount, currency=currency)

    def update(self, threshold: Threshold, *, amount: Decimal, currency: str) -> Threshold:
        threshold.amount = amount
        threshold.currency = currency
        threshold.save(update_fields=["amount", "currency", "updated_at"])
        return threshold

    def delete(self, threshold: Threshold) -> None:
        threshold.delete()


class PriceAlertRepository:
    """Data-access layer for PriceAlert."""

    def get_by_id(self, alert_id: int) -> Optional[PriceAlert]:
        try:
            return PriceAlert.objects.select_related(
                "user", "flight_route", "threshold"
            ).get(pk=alert_id)
        except PriceAlert.DoesNotExist:
            return None

    def create(
        self,
        *,
        user,
        flight_route: FlightRoute,
        threshold: Threshold,
        travel_date=None,
    ) -> PriceAlert:
        return PriceAlert.objects.create(
            user=user,
            flight_route=flight_route,
            threshold=threshold,
            travel_date=travel_date,
        )

    def list_for_user(self, user) -> QuerySet[PriceAlert]:
        return PriceAlert.objects.select_related(
            "flight_route", "threshold"
        ).filter(user=user)

    def list_active(self) -> QuerySet[PriceAlert]:
        return PriceAlert.objects.select_related(
            "user", "flight_route", "threshold"
        ).filter(status=PriceAlert.Status.ACTIVE)

    def list_active_for_route(self, route: FlightRoute) -> QuerySet[PriceAlert]:
        return PriceAlert.objects.select_related(
            "user", "threshold"
        ).filter(flight_route=route, status=PriceAlert.Status.ACTIVE)

    def update_status(self, alert: PriceAlert, status: str) -> PriceAlert:
        alert.status = status
        alert.save(update_fields=["status", "updated_at"])
        return alert

    def delete(self, alert: PriceAlert) -> None:
        alert.delete()


class NotificationRepository:
    """Data-access layer for Notification."""

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        try:
            return Notification.objects.select_related("user", "price_alert").get(
                pk=notification_id
            )
        except Notification.DoesNotExist:
            return None

    def create(
        self,
        *,
        user,
        price_alert: PriceAlert,
        channel: str,
        message: str,
        triggered_price: Decimal,
    ) -> Notification:
        return Notification.objects.create(
            user=user,
            price_alert=price_alert,
            channel=channel,
            message=message,
            triggered_price=triggered_price,
        )

    def list_for_user(self, user) -> QuerySet[Notification]:
        return Notification.objects.filter(user=user)

    def list_unread_for_user(self, user) -> QuerySet[Notification]:
        return Notification.objects.filter(user=user, is_read=False)

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return notification

    def mark_sent(self, notification: Notification, sent_at) -> Notification:
        from django.utils import timezone

        notification.status = Notification.Status.SENT
        notification.sent_at = sent_at or timezone.now()
        notification.save(update_fields=["status", "sent_at"])
        return notification

    def mark_failed(self, notification: Notification) -> Notification:
        notification.status = Notification.Status.FAILED
        notification.save(update_fields=["status"])
        return notification

    def delete(self, notification: Notification) -> None:
        notification.delete()
