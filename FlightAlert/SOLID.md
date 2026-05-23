# SOLID Principles

## S - Single Responsibility Principle (SRP)
A class/module shave have one reason to change

```python
class OrderView(APIView):

    def post(self, request):
        # validation
        # payment
        # inventory
        # email
        # analytics
        # response formatting
```        
Better design would be - service, repo, util etc

```python
# views.py
class OrderView(APIView):

    def post(self, request):
        order = order_service.place_order(request.data)
        return Response(order)

# services/order_service.py

def place_order(data):
    validate_order(data)
    reserve_inventory(data)
    process_payment(data)
    send_confirmation(data)
```

## O - Open/Closed Principle (OCP)
Open for extension and closed for modifcation.
Avoid modifyinhg existing stavle code whenever new behavior is added.

```python
def send_notification(type, data):
    if type == "EMAIL":
        ...
    elif type == "SMS":
        ...
    elif type == "PUSH":
        ...
```

Better Design:
```python
class NotificationSender:
    def send(self, data):
        raise NotImplementedError

class EmailSender(NotificationSender):
    def send(self, data):
        ...

class SmsSender(NotificationSender):
    def send(self, data):
        ...
```

## L - Liskov Substituion Principle (LSP)
Child classes should safely replace parent classes:

```python
class Bird:
    def fly(self):
        pass


class Penguin(Bird):
    def fly(self):
        raise Exception("Cannot fly")
```

Broken Substitution

Better design:
```python
class Bird:
    pass


class FlyingBird(Bird):
    def fly(self):
        pass
```
Use inheritance only when behavior truly matches.

# I - Interface Segregation Principle (ISP)
Don’t force classes to implement methods they don’t need.

```python
class PaymentGateway:
    def pay(self):
        pass

    def refund(self):
        pass

    def create_subscription(self):
        pass
```

Some gateways may not support subscriptions.

Better:
```python
class PaymentGateway:
    def pay(self):
        pass

class RefundableGateway:
    def refund(self):
        pass
```
Smaller focused contracts.

## D — Dependency Inversion Principle (DIP)
Depend on abstractions, not concrete implementations.

```python
class OrderService:

    def process(self):
        razorpay = RazorpayClient()
        razorpay.pay()
```

Better:
```python
class PaymentGateway:
    def pay(self):
        pass

class OrderService:

    def __init__(self, gateway):
        self.gateway = gateway

    def process(self):
        self.gateway.pay()
```      