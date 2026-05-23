import logging
from decimal import Decimal

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from django.utils import timezone

logger = get_task_logger(__name__)


# ── Task 1: Periodic beat entry-point ────────────────────────────────────────


@shared_task(bind=True, name="flights.check_all_alerts")
def check_all_alerts(self) -> dict:
    """
    Periodic entry-point (configured in CELERY_BEAT_SCHEDULE).

    Queries all unique routes that have at least one active alert and
    fans out one `check_route_price` task per route.  Keeping tasks
    per-route means failures are isolated and retried independently.
    """
    from .repositories import PriceAlertRepository

    active_alerts = list(PriceAlertRepository().list_active())

    if not active_alerts:
        logger.info("check_all_alerts: no active alerts, nothing to dispatch.")
        return {"routes_dispatched": 0}

    unique_route_ids: set[int] = {a.flight_route_id for a in active_alerts}

    for route_id in unique_route_ids:
        check_route_price.delay(route_id)

    logger.info(
        "check_all_alerts: dispatched %d check_route_price task(s).",
        len(unique_route_ids),
    )
    return {"routes_dispatched": len(unique_route_ids)}


# ── Task 2: Price fetch + threshold check for a single route ─────────────────


@shared_task(
    bind=True,
    name="flights.check_route_price",
    max_retries=3,
    default_retry_delay=120,
)
def check_route_price(self, route_id: int) -> dict:
    """
    Fetch the current price for *route_id*, check every active alert
    against the threshold, create Notification records, and fan out
    `send_email_notification` for each email channel record.

    Swap `_get_price_fetcher()` for a real API client (Amadeus,
    Skyscanner, etc.) once available.
    """
    from .models import Notification, PriceAlert
    from .repositories import FlightRouteRepository, PriceAlertRepository
    from .services import NotificationService

    route = FlightRouteRepository().get_by_id(route_id)
    if route is None:
        logger.warning("check_route_price: route id=%d not found, skipping.", route_id)
        return {"skipped": True, "reason": "route not found"}

    try:
        price: Decimal | None = _get_price_fetcher().fetch_price(route)
    except Exception as exc:
        logger.exception(
            "check_route_price: price fetch failed for route id=%d", route_id
        )
        raise self.retry(exc=exc)

    if price is None:
        logger.warning(
            "check_route_price: no price returned for route %s→%s (id=%d), skipping.",
            route.origin,
            route.destination,
            route_id,
        )
        return {"skipped": True, "reason": "no price available"}

    logger.info(
        "check_route_price: route %s→%s price=%s",
        route.origin,
        route.destination,
        price,
    )

    alert_repo = PriceAlertRepository()
    notification_service = NotificationService()
    active_alerts = list(alert_repo.list_active_for_route(route))
    notification_ids: list[int] = []

    for alert in active_alerts:
        if not alert.check_price(price):
            continue

        logger.info(
            "check_route_price: threshold breached for alert id=%d "
            "(price=%s, threshold=%s)",
            alert.pk,
            price,
            alert.threshold.amount,
        )

        # Create pending records without dispatching — tasks handle dispatch.
        notifications = notification_service.create_pending_notifications(
            alert=alert, triggered_price=price
        )
        alert_repo.update_status(alert, PriceAlert.Status.TRIGGERED)

        for notification in notifications:
            notification_ids.append(notification.pk)
            if notification.channel == Notification.Channel.EMAIL:
                send_email_notification.delay(notification.pk)
            # in_app: record already exists; no external call needed.
            # sms: extend by adding an SMS task here when ready.

    return {
        "route_id": route_id,
        "price": str(price),
        "alerts_checked": len(active_alerts),
        "notifications_created": len(notification_ids),
    }


# ── Task 3: Send a single email notification via Brevo ───────────────────────


@shared_task(
    bind=True,
    name="flights.send_email_notification",
    max_retries=3,
)
def send_email_notification(self, notification_id: int) -> dict:
    """
    Send one email notification via Brevo (AlertNotifier).

    Retries up to 3 times with exponential back-off on failure.
    Idempotent: exits immediately if the notification is already sent.
    """
    from .notifiers import AlertNotifier
    from .repositories import NotificationRepository

    repo = NotificationRepository()
    notification = repo.get_by_id(notification_id)

    if notification is None:
        logger.warning(
            "send_email_notification: notification id=%d not found.", notification_id
        )
        return {"skipped": True, "reason": "not found"}

    if notification.status == "sent":
        logger.info(
            "send_email_notification: notification id=%d already sent, skipping.",
            notification_id,
        )
        return {"skipped": True, "reason": "already sent"}

    notifier = AlertNotifier()
    success = notifier.send_email(notification=notification)

    if success:
        repo.mark_sent(notification, sent_at=timezone.now())
        logger.info(
            "send_email_notification: notification id=%d sent.", notification_id
        )
        return {"notification_id": notification_id, "success": True}

    # Retry with exponential back-off (60s, 120s, 240s).
    retry_countdown = 60 * (2 ** self.request.retries)
    logger.warning(
        "send_email_notification: dispatch failed for id=%d, "
        "retry %d/%d in %ds.",
        notification_id,
        self.request.retries + 1,
        self.max_retries,
        retry_countdown,
    )
    try:
        raise self.retry(countdown=retry_countdown)
    except MaxRetriesExceededError:
        repo.mark_failed(notification)
        logger.error(
            "send_email_notification: max retries exceeded for id=%d, "
            "marked as failed.",
            notification_id,
        )
        return {"notification_id": notification_id, "success": False}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_price_fetcher():
    """
    Return the configured price fetcher.

    Reads FLIGHT_PRICE_FETCHER from Django settings:
      - "mock"  (default) → MockPriceFetcher for local dev / tests
      - Any other value → raise NotImplementedError (plug in a real client here)
    """
    from django.conf import settings

    from .checkers import MockPriceFetcher

    fetcher_name: str = getattr(settings, "FLIGHT_PRICE_FETCHER", "mock")

    if fetcher_name == "mock":
        return MockPriceFetcher()

    raise NotImplementedError(
        f"Unknown FLIGHT_PRICE_FETCHER={fetcher_name!r}. "
        "Implement a real PriceFetcher and register it here."
    )
