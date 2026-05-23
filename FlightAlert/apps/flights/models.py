from decimal import Decimal

from django.conf import settings
from django.db import models


class FlightRoute(models.Model):
    origin = models.CharField(max_length=3, help_text="IATA airport code, e.g. BOM")
    destination = models.CharField(max_length=3, help_text="IATA airport code, e.g. DEL")
    airline = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "flight_routes"
        unique_together = ("origin", "destination", "airline")
        verbose_name = "Flight Route"
        verbose_name_plural = "Flight Routes"

    def __str__(self) -> str:
        return f"{self.origin} → {self.destination} ({self.airline or 'Any'})"


class Threshold(models.Model):
    class Currency(models.TextChoices):
        INR = "INR", "Indian Rupee"
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"
        GBP = "GBP", "British Pound"

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.INR)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "thresholds"
        verbose_name = "Threshold"
        verbose_name_plural = "Thresholds"

    def __str__(self) -> str:
        return f"{self.currency} {self.amount}"

    def is_breached_by(self, price: Decimal) -> bool:
        """Return True when the given price is at or below this threshold."""
        return price <= self.amount


class PriceAlert(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        TRIGGERED = "triggered", "Triggered"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="price_alerts",
    )
    flight_route = models.ForeignKey(
        FlightRoute,
        on_delete=models.CASCADE,
        related_name="price_alerts",
    )
    threshold = models.OneToOneField(
        Threshold,
        on_delete=models.CASCADE,
        related_name="price_alert",
    )
    current_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    travel_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "price_alerts"
        verbose_name = "Price Alert"
        verbose_name_plural = "Price Alerts"

    def __str__(self) -> str:
        return f"Alert [{self.user}] {self.flight_route} ≤ {self.threshold}"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    def check_price(self, price: Decimal) -> bool:
        """Update current price and return True if threshold is breached."""
        self.current_price = price
        self.save(update_fields=["current_price", "updated_at"])
        return self.threshold.is_breached_by(price)


class Notification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        IN_APP = "in_app", "In-App"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    price_alert = models.ForeignKey(
        PriceAlert,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(
        max_length=10, choices=Channel.choices, default=Channel.IN_APP
    )
    message = models.TextField()
    triggered_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self) -> str:
        return f"Notification [{self.channel}] → {self.user} ({self.status})"
