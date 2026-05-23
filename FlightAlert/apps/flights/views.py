from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    FlightRouteSerializer,
    NotificationSerializer,
    PriceAlertCreateSerializer,
    PriceAlertSerializer,
    PriceUpdateSerializer,
)
from .services import FlightRouteService, NotificationService, PriceAlertService


class FlightRouteListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FlightRouteService()

    def get(self, request: Request) -> Response:
        origin = request.query_params.get("origin")
        destination = request.query_params.get("destination")
        if origin and destination:
            routes = self.service.search_routes(origin=origin, destination=destination)
        else:
            routes = self.service.list_active_routes()
        return Response(FlightRouteSerializer(routes, many=True).data)


class PriceAlertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PriceAlertService()

    def get(self, request: Request) -> Response:
        alerts = self.service.list_alerts_for_user(request.user)
        return Response(PriceAlertSerializer(alerts, many=True).data)

    # TODO: Avoid creation for duplication of alerts
    # A person can only have at most 10 active alerts at a given time.
    def post(self, request: Request) -> Response:
        serializer = PriceAlertCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            alert = self.service.create_alert(user=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PriceAlertSerializer(alert).data, status=status.HTTP_201_CREATED)


class PriceAlertDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PriceAlertService()

    def _get_alert_for_user(self, alert_id: int, user):
        try:
            alert = self.service.get_alert(alert_id)
        except ValueError as exc:
            return None, Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if alert.user_id != user.pk:
            return None, Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return alert, None

    def get(self, request: Request, pk: int) -> Response:
        alert, err = self._get_alert_for_user(pk, request.user)
        if err:
            return err
        return Response(PriceAlertSerializer(alert).data)

    def delete(self, request: Request, pk: int) -> Response:
        alert, err = self._get_alert_for_user(pk, request.user)
        if err:
            return err
        self.service.delete_alert(alert)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PriceAlertPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PriceAlertService()

    def post(self, request: Request, pk: int) -> Response:
        try:
            alert = self.service.get_alert(pk)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if alert.user_id != request.user.pk:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert = self.service.pause_alert(alert)
        return Response(PriceAlertSerializer(alert).data)


class PriceAlertResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PriceAlertService()

    def post(self, request: Request, pk: int) -> Response:
        try:
            alert = self.service.get_alert(pk)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if alert.user_id != request.user.pk:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert = self.service.resume_alert(alert)
        return Response(PriceAlertSerializer(alert).data)


class PriceUpdateView(APIView):
    """
    Simulates an incoming price update (e.g. from a price-scraping worker).
    In production this would be called by an internal service, not end users.
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alert_service = PriceAlertService()
        self.route_service = FlightRouteService()

    def post(self, request: Request) -> Response:
        serializer = PriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            route = self.route_service.get_route(serializer.validated_data["route_id"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        notifications = self.alert_service.process_price_update(
            route=route, new_price=serializer.validated_data["new_price"]
        )
        return Response(
            {
                "notifications_triggered": len(notifications),
                "notifications": NotificationSerializer(notifications, many=True).data,
            }
        )


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = NotificationService()

    def get(self, request: Request) -> Response:
        only_unread = request.query_params.get("unread") == "true"
        if only_unread:
            notifications = self.service.list_unread_for_user(request.user)
        else:
            notifications = self.service.list_for_user(request.user)
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = NotificationService()

    def post(self, request: Request, pk: int) -> Response:
        try:
            notification = self.service.get_notification(pk)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if notification.user_id != request.user.pk:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        notification = self.service.mark_read(notification)
        return Response(NotificationSerializer(notification).data)
