import logging
from typing import Protocol

from django.conf import settings

from .models import Notification

logger = logging.getLogger(__name__)


class EmailNotifierProtocol(Protocol):
    """Any object that can dispatch an email notification."""

    def send_email(self, *, notification: Notification) -> bool: ...


class AlertNotifier:
    """
    Sends email notifications for triggered price alerts via Brevo.

    Requires BREVO_API_KEY, BREVO_SENDER_EMAIL in Django settings.
    BREVO_SENDER_NAME is optional (defaults to "FlightAlert").
    """

    def __init__(self) -> None:
        from brevo import Brevo

        self._client = Brevo(api_key=settings.BREVO_API_KEY)
        self._sender_email: str = settings.BREVO_SENDER_EMAIL
        self._sender_name: str = getattr(settings, "BREVO_SENDER_NAME", "FlightAlert")

    def send_email(self, *, notification: Notification) -> bool:
        """
        Send a price-alert email via Brevo.
        Returns True on success, False on any dispatch error.
        """
        from brevo.transactional_emails import (
            SendTransacEmailRequestSender,
            SendTransacEmailRequestToItem,
        )

        user = notification.user
        recipient_name = user.get_full_name() or user.username

        try:
            result = self._client.transactional_emails.send_transac_email(
                subject="Flight Price Alert Triggered!",
                html_content=self._build_html(notification),
                sender=SendTransacEmailRequestSender(
                    email=self._sender_email,
                    name=self._sender_name,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        email=user.email,
                        name=recipient_name,
                    )
                ],
            )
            logger.info(
                "Brevo email sent for notification %s (message_id=%s)",
                notification.pk,
                getattr(result, "message_id", "n/a"),
            )
            return True
        except Exception:
            logger.exception(
                "Brevo email dispatch failed for notification %s", notification.pk
            )
            return False

    @staticmethod
    def _build_html(notification: Notification) -> str:
        route = notification.price_alert.flight_route
        threshold = notification.price_alert.threshold
        currency = threshold.currency
        return f"""
        <html>
          <body style="font-family: sans-serif; color: #333; max-width: 520px; margin: 0 auto;">
            <h2 style="color: #1a56db;">Flight Price Alert Triggered!</h2>
            <p>{notification.message}</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
              <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Route</strong></td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">
                  {route.origin} &rarr; {route.destination}
                  {f' ({route.airline})' if route.airline else ''}
                </td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Current Price</strong></td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">
                  {currency} {notification.triggered_price:.2f}
                </td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Your Threshold</strong></td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">
                  {currency} {threshold.amount:.2f}
                </td>
              </tr>
            </table>
            <p style="margin-top: 24px; font-size: 12px; color: #6b7280;">
              You received this email because you set a price alert on FlightAlert.
            </p>
          </body>
        </html>
        """
