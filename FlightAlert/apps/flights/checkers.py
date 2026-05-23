import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from .models import FlightRoute, Notification, PriceAlert

logger = logging.getLogger(__name__)


# ── Price fetcher protocol ────────────────────────────────────────────────────


class PriceFetcher(Protocol):
    """
    Contract for any price-fetching backend.

    Implement this protocol to plug in a real flight-price API
    (e.g. Amadeus, Skyscanner, Google Flights).
    """

    def fetch_price(self, route: FlightRoute) -> Decimal | None:
        """
        Return the current lowest price for the given route,
        or None if the price is unavailable / the API is unreachable.
        """
        ...


class MockPriceFetcher:
    """
    Deterministic stub for tests and local development.

    Pass a mapping of route-id → price, or a fixed fallback price.
    Any route not in the map returns the fallback (default: None).
    """

    def __init__(
        self,
        prices: dict[int, Decimal] | None = None,
        fallback: Decimal | None = None,
    ) -> None:
        self._prices: dict[int, Decimal] = prices or {}
        self._fallback = fallback

    def fetch_price(self, route: FlightRoute) -> Decimal | None:
        return self._prices.get(route.pk, self._fallback)


# ── Result data classes ───────────────────────────────────────────────────────


@dataclass
class RouteCheckResult:
    route_id: int
    origin: str
    destination: str
    price_fetched: Decimal | None
    notifications_triggered: int
    error: str | None = None


@dataclass
class AlertCheckSummary:
    routes_checked: int = 0
    routes_skipped: int = 0
    notifications_triggered: int = 0
    results: list[RouteCheckResult] = field(default_factory=list)


# ── AlertChecker ──────────────────────────────────────────────────────────────


class AlertChecker:
    """
    Checks current flight prices against all active user alerts and
    fires notifications for any threshold breaches.

    Usage (e.g. in a management command or Celery beat task)::

        fetcher = MyRealPriceFetcher()          # implements PriceFetcher
        checker = AlertChecker(price_fetcher=fetcher)
        summary = checker.run()
        print(summary.notifications_triggered)

    For tests::

        fetcher = MockPriceFetcher(prices={route.pk: Decimal("4500")})
        checker = AlertChecker(price_fetcher=fetcher)
        summary = checker.run()
    """

    def __init__(
        self,
        price_fetcher: PriceFetcher,
        alert_service=None,
    ) -> None:
        from .services import PriceAlertService

        self._fetcher = price_fetcher
        self._alert_service = alert_service or PriceAlertService()

    def run(self) -> AlertCheckSummary:
        """
        Main entry point.

        1. Loads all active PriceAlerts (one DB query via select_related).
        2. De-duplicates routes so each route is priced only once.
        3. For each route, fetches the current price and delegates to
           PriceAlertService.process_price_update() which handles threshold
           comparison, status updates, and notification dispatch.
        """
        summary = AlertCheckSummary()

        active_alerts: list[PriceAlert] = list(
            self._alert_service.alert_repo.list_active()
        )

        if not active_alerts:
            logger.info("AlertChecker: no active alerts found, nothing to check.")
            return summary

        # De-duplicate routes; preserve the FlightRoute object
        unique_routes: dict[int, FlightRoute] = {
            alert.flight_route_id: alert.flight_route for alert in active_alerts
        }

        logger.info(
            "AlertChecker: %d active alert(s) across %d route(s).",
            len(active_alerts),
            len(unique_routes),
        )

        for route in unique_routes.values():
            result = self._check_route(route)
            summary.results.append(result)
            summary.routes_checked += 1
            summary.notifications_triggered += result.notifications_triggered
            if result.price_fetched is None:
                summary.routes_skipped += 1

        logger.info(
            "AlertChecker finished: %d route(s) checked, %d skipped, "
            "%d notification(s) triggered.",
            summary.routes_checked,
            summary.routes_skipped,
            summary.notifications_triggered,
        )
        return summary

    # ------------------------------------------------------------------

    def _check_route(self, route: FlightRoute) -> RouteCheckResult:
        result = RouteCheckResult(
            route_id=route.pk,
            origin=route.origin,
            destination=route.destination,
            price_fetched=None,
            notifications_triggered=0,
        )

        try:
            price = self._fetcher.fetch_price(route)
        except Exception as exc:
            logger.exception(
                "AlertChecker: price fetch failed for route %s→%s (id=%d)",
                route.origin,
                route.destination,
                route.pk,
            )
            result.error = str(exc)
            return result

        if price is None:
            logger.warning(
                "AlertChecker: no price returned for route %s→%s (id=%d), skipping.",
                route.origin,
                route.destination,
                route.pk,
            )
            return result

        result.price_fetched = price

        try:
            notifications: list[Notification] = (
                self._alert_service.process_price_update(
                    route=route, new_price=price
                )
            )
            result.notifications_triggered = len(notifications)
        except Exception as exc:
            logger.exception(
                "AlertChecker: process_price_update failed for route id=%d", route.pk
            )
            result.error = str(exc)

        return result
