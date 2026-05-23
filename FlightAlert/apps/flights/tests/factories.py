from decimal import Decimal

import factory

from apps.flights.models import FlightRoute, Notification, PriceAlert, Threshold
from apps.users.tests.factories import UserFactory


class FlightRouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlightRoute

    origin = factory.Iterator(["BOM", "DEL", "BLR", "MAA"])
    destination = factory.Iterator(["DEL", "BOM", "MAA", "BLR"])
    airline = factory.Iterator(["IndiGo", "Air India", "SpiceJet", "Vistara"])
    is_active = True


class ThresholdFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Threshold

    amount = factory.LazyFunction(lambda: Decimal("5000.00"))
    currency = Threshold.Currency.INR


class PriceAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PriceAlert

    user = factory.SubFactory(UserFactory)
    flight_route = factory.SubFactory(FlightRouteFactory)
    threshold = factory.SubFactory(ThresholdFactory)
    status = PriceAlert.Status.ACTIVE


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    price_alert = factory.SubFactory(PriceAlertFactory)
    channel = Notification.Channel.IN_APP
    message = factory.Faker("sentence")
    triggered_price = factory.LazyFunction(lambda: Decimal("4500.00"))
    status = Notification.Status.SENT
