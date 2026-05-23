from rest_framework import serializers

from .models import FlightRoute, Notification, PriceAlert, Threshold


class FlightRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightRoute
        fields = ["id", "origin", "destination", "airline", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]


class ThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Threshold
        fields = ["id", "amount", "currency"]
        read_only_fields = ["id"]


class PriceAlertCreateSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=3, min_length=3)
    destination = serializers.CharField(max_length=3, min_length=3)
    airline = serializers.CharField(max_length=100, required=False, default="")
    threshold_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    threshold_currency = serializers.ChoiceField(
        choices=Threshold.Currency.choices, default=Threshold.Currency.INR
    )
    travel_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, data):
        if data["origin"].upper() == data["destination"].upper():
            raise serializers.ValidationError("Origin and destination cannot be the same.")
        return data


class PriceAlertSerializer(serializers.ModelSerializer):
    flight_route = FlightRouteSerializer(read_only=True)
    threshold = ThresholdSerializer(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = PriceAlert
        fields = [
            "id",
            "user_email",
            "flight_route",
            "threshold",
            "current_price",
            "status",
            "travel_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_email", "current_price", "status", "created_at", "updated_at"]


class PriceUpdateSerializer(serializers.Serializer):
    """Used to simulate a price update for a route (e.g. from a price scraper)."""

    route_id = serializers.IntegerField()
    new_price = serializers.DecimalField(max_digits=12, decimal_places=2)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "price_alert",
            "channel",
            "message",
            "triggered_price",
            "status",
            "is_read",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
