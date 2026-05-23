from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import LoginView, NotificationPreferenceView, ProfileView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="user-register"),
    path("login/", LoginView.as_view(), name="user-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("profile/", ProfileView.as_view(), name="user-profile"),
    path(
        "profile/notifications/",
        NotificationPreferenceView.as_view(),
        name="user-notification-prefs",
    ),
]
