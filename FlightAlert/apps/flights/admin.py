from django.contrib import admin

from .models import FlightRoute, Notification, PriceAlert, Threshold


@admin.register(FlightRoute)
class FlightRouteAdmin(admin.ModelAdmin):
    list_display = ["origin", "destination", "airline", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["origin", "destination", "airline"]


@admin.register(Threshold)
class ThresholdAdmin(admin.ModelAdmin):
    list_display = ["amount", "currency", "created_at"]
    list_filter = ["currency"]


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ["user", "flight_route", "threshold", "current_price", "status", "travel_date"]
    list_filter = ["status"]
    search_fields = ["user__email", "flight_route__origin", "flight_route__destination"]
    raw_id_fields = ["user", "flight_route", "threshold"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "channel", "status", "is_read", "sent_at", "created_at"]
    list_filter = ["channel", "status", "is_read"]
    search_fields = ["user__email"]
    raw_id_fields = ["user", "price_alert"]
