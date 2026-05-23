import logging
from decimal import Decimal

from django.utils import timezone

from .models import FlightRoute, Notification, PriceAlert, Threshold
from .repositories import (
    FlightRouteRepository,
    NotificationRepository,
    PriceAlertRepository,
    ThresholdRepository,
)

logger = logging.getLogger(__name__)


class FlightRouteService:
    """Business logic for flight routes."""

    def __init__(self, repository: FlightRouteRepository | None = None) -> None:
        self.repository = repository or FlightRouteRepository()

    def get_or_create_route(
        self, *, origin: str, destination: str, airline: str = ""
    ) -> tuple[FlightRoute, bool]:
        if origin.upper() == destination.upper():
            raise ValueError("Origin and destination cannot be the same.")
        return self.repository.get_or_create(
            origin=origin, destination=destination, airline=airline
        )

    def list_active_routes(self):
        return self.repository.list_active()

    def search_routes(self, *, origin: str, destination: str):
        return self.repository.search(origin=origin, destination=destination)

    def get_route(self, route_id: int) -> FlightRoute:
        route = self.repository.get_by_id(route_id)
        if route is None:
            raise ValueError(f"FlightRoute with id={route_id} not found.")
        return route


class PriceAlertService:
    """Business logic for price alerts."""

    def __init__(
        self,
        alert_repo: PriceAlertRepository | None = None,
        threshold_repo: ThresholdRepository | None = None,
        route_service: FlightRouteService | None = None,
        notification_service: "NotificationService | None" = None,
    ) -> None:
        self.alert_repo = alert_repo or PriceAlertRepository()
        self.threshold_repo = threshold_repo or ThresholdRepository()
        self.route_service = route_service or FlightRouteService()
        self.notification_service = notification_service or NotificationService()

    def create_alert(
        self,
        *,
        user,
        origin: str,
        destination: str,
        airline: str = "",
        threshold_amount: Decimal,
        threshold_currency: str = "INR",
        travel_date=None,
    ) -> PriceAlert:
        route, _ = self.route_service.get_or_create_route(
            origin=origin, destination=destination, airline=airline
        )
        threshold = self.threshold_repo.create(
            amount=threshold_amount, currency=threshold_currency
        )
        return self.alert_repo.create(
            user=user,
            flight_route=route,
            threshold=threshold,
            travel_date=travel_date,
        )

    def get_alert(self, alert_id: int) -> PriceAlert:
        alert = self.alert_repo.get_by_id(alert_id)
        if alert is None:
            raise ValueError(f"PriceAlert with id={alert_id} not found.")
        return alert

    def list_alerts_for_user(self, user):
        return self.alert_repo.list_for_user(user)

    def pause_alert(self, alert: PriceAlert) -> PriceAlert:
        return self.alert_repo.update_status(alert, PriceAlert.Status.PAUSED)

    def resume_alert(self, alert: PriceAlert) -> PriceAlert:
        return self.alert_repo.update_status(alert, PriceAlert.Status.ACTIVE)

    def delete_alert(self, alert: PriceAlert) -> None:
        self.alert_repo.delete(alert)

    def process_price_update(
        self, *, route: FlightRoute, new_price: Decimal
    ) -> list[Notification]:
        """
        Called when a new price is available for a route.
        Checks all active alerts for the route and fires notifications
        when the price drops at or below the alert threshold.
        """
        triggered_notifications: list[Notification] = []
        active_alerts = self.alert_repo.list_active_for_route(route)

        for alert in active_alerts:
            if alert.check_price(new_price):
                logger.info(
                    "Threshold breached for alert %s: price=%s threshold=%s",
                    alert.pk,
                    new_price,
                    alert.threshold.amount,
                )
                notifications = self.notification_service.send_alert_notification(
                    alert=alert, triggered_price=new_price
                )
                triggered_notifications.extend(notifications)
                self.alert_repo.update_status(alert, PriceAlert.Status.TRIGGERED)

        return triggered_notifications


class NotificationService:
    """Business logic for sending and managing notifications."""

    def __init__(
        self,
        repository: NotificationRepository | None = None,
        email_notifier=None,
    ) -> None:
        self.repository = repository or NotificationRepository()
        self._email_notifier = email_notifier

    def send_alert_notification(
        self, *, alert: PriceAlert, triggered_price: Decimal
    ) -> list[Notification]:
        """
        Creates notification records for all enabled channels of the alert owner.
        In a real system, this would dispatch to email/SMS providers.
        """
        user = alert.user
        channels = self._resolve_channels(user)
        message = self._build_message(alert=alert, triggered_price=triggered_price)
        notifications: list[Notification] = []

        for channel in channels:
            notification = self.repository.create(
                user=user,
                price_alert=alert,
                channel=channel,
                message=message,
                triggered_price=triggered_price,
            )
            notification = self._dispatch(notification)
            notifications.append(notification)

        return notifications

    def create_pending_notifications(
        self, *, alert: PriceAlert, triggered_price: Decimal
    ) -> list[Notification]:
        """
        Create Notification records in PENDING status for all enabled channels
        without dispatching them. Used by Celery tasks to fan out sends.
        """
        user = alert.user
        channels = self._resolve_channels(user)
        message = self._build_message(alert=alert, triggered_price=triggered_price)
        return [
            self.repository.create(
                user=user,
                price_alert=alert,
                channel=channel,
                message=message,
                triggered_price=triggered_price,
            )
            for channel in channels
        ]

    def list_for_user(self, user):
        return self.repository.list_for_user(user)

    def list_unread_for_user(self, user):
        return self.repository.list_unread_for_user(user)

    def mark_read(self, notification: Notification) -> Notification:
        return self.repository.mark_read(notification)

    def get_notification(self, notification_id: int) -> Notification:
        notification = self.repository.get_by_id(notification_id)
        if notification is None:
            raise ValueError(f"Notification with id={notification_id} not found.")
        return notification

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_channels(self, user) -> list[str]:
        channels = [Notification.Channel.IN_APP]
        if user.notification_email:
            channels.append(Notification.Channel.EMAIL)
        if user.notification_sms and user.phone_number:
            channels.append(Notification.Channel.SMS)
        return channels

    @staticmethod
    def _build_message(*, alert: PriceAlert, triggered_price: Decimal) -> str:
        route = alert.flight_route
        currency = alert.threshold.currency
        return (
            f"Price alert triggered! {route.origin} → {route.destination} "
            f"is now {currency} {triggered_price:.2f}, "
            f"which is at or below your threshold of {currency} {alert.threshold.amount:.2f}."
        )

    def _dispatch(self, notification: Notification) -> Notification:
        """
        Dispatch a notification to its channel.

        - email  → Brevo (AlertNotifier); lazily instantiated unless injected.
        - sms    → placeholder (extend with an SMS provider as needed).
        - in_app → recorded in DB only; no external call required.
        """
        logger.info(
            "Dispatching %s notification to user %s",
            notification.channel,
            notification.user_id,
        )
        try:
            if notification.channel == Notification.Channel.EMAIL:
                notifier = self._email_notifier or self._get_email_notifier()
                success = notifier.send_email(notification=notification)
                if not success:
                    return self.repository.mark_failed(notification)
            elif notification.channel == Notification.Channel.SMS:
                # Extend here with an SMS provider (e.g. Twilio, Brevo SMS).
                logger.warning(
                    "SMS dispatch not implemented; marking notification %s as failed.",
                    notification.pk,
                )
                return self.repository.mark_failed(notification)
            # in_app notifications need no external call
            return self.repository.mark_sent(notification, sent_at=timezone.now())
        except Exception:
            logger.exception("Failed to dispatch notification %s", notification.pk)
            return self.repository.mark_failed(notification)

    @staticmethod
    def _get_email_notifier():
        """Lazily import to avoid import errors when BREVO_API_KEY is not set."""
        from .notifiers import AlertNotifier

        return AlertNotifier()
