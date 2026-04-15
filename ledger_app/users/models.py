import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):

    def create_user(self, phone_number, password=None, **extra_fields):
        """
        This function overrides the create_user function in BaseUserManager.
        Its job is to create a user. We are overriding because we want our 
        own custom logic while creating a user.
        """
        if not phone_number:
            raise ValueError("Phone number is required")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.password = password  # expects a pre-hashed value from bcrypt_util
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser):

    class UserType(models.TextChoices):
        BASIC = "BASIC_USER", "Basic User"
        PREMIUM = "PREMIUM_USER", "Premium User"

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        NON_ADMIN = "NON_ADMIN", "Non Admin"

    BASIC_DAILY_LIMIT = 50_000

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    dob = models.DateField()
    phone_number = models.CharField(max_length=15, blank=False, unique=True)
    is_active = models.BooleanField(default=True)
    user_type = models.CharField(
        max_length=20, choices=UserType.choices, default=UserType.BASIC
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.NON_ADMIN
    )
    default_account = models.ForeignKey(
        "Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_for_user",
    )

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name", "last_name", "dob"]

    objects: UserManager = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Account(models.Model):
    class AccountType(models.TextChoices):
        SAVINGS = "SAVINGS"
        CURRENT = "CURRENT"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accounts")
    account_number = models.CharField(max_length=30, unique=True)
    ifsc = models.CharField(max_length=11)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_type = models.CharField(
        max_length=10, choices=AccountType.choices, default=AccountType.SAVINGS
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # toString()
    def __str__(self):
        return f"{self.account_number} ({self.account_type})"


class Category(models.TextChoices):
    HOUSEHOLD = "HOUSEHOLD", "Household"
    LEISURE = "LEISURE", "Leisure"
    TRAVEL = "TRAVEL", "Travel"
    MISCELLANEOUS = "MISCELLANEOUS", "Miscellaneous"


class PaymentMethod(models.TextChoices):
    UPI = "UPI"
    CC = "CC", "Credit Card"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"


class Transaction(models.Model):

    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="outgoing_transactions"
    )
    to_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="incoming_transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True, default="")
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PROCESSING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.txn_id} | {self.amount} ({self.status})"


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=20, choices=Category.choices)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
