from django.urls import path

from .views import (
    FlightRouteListView,
    NotificationListView,
    NotificationMarkReadView,
    PriceAlertDetailView,
    PriceAlertListCreateView,
    PriceAlertPauseView,
    PriceAlertResumeView,
    PriceUpdateView,
)

urlpatterns = [
    path("routes/", FlightRouteListView.as_view(), name="route-list"),
    path("alerts/", PriceAlertListCreateView.as_view(), name="alert-list-create"),
    path("alerts/<int:pk>/", PriceAlertDetailView.as_view(), name="alert-detail"),
    path("alerts/<int:pk>/pause/", PriceAlertPauseView.as_view(), name="alert-pause"),
    path("alerts/<int:pk>/resume/", PriceAlertResumeView.as_view(), name="alert-resume"),
    path("prices/update/", PriceUpdateView.as_view(), name="price-update"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
]
