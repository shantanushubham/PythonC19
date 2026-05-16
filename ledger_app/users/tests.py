from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .bcrypt_util import hash_password
from .models import Account, Budget, Category, PaymentMethod, Transaction, User
from .my_test import add_two_numbers


# ---------------------------------------------------------------------------
# add_two_numbers unit tests
# ---------------------------------------------------------------------------

class AddTwoNumbersTest(TestCase):

  # Situation 1: both numbers are positive and within range
  def test_add_positive_numbers(self):
    result = add_two_numbers(2, 3)
    self.assertEqual(result, 5)

  # Situation 2: both numbers are negative — should raise Exception
  def test_add_negative_numbers(self):
    with self.assertRaises(Exception) as ctx:
      add_two_numbers(-1, -2)
    self.assertEqual(str(ctx.exception), 'Numbers have to be positive')

  # Situation 3: one negative, one positive — should raise Exception
  def test_add_mixed_numbers(self):
    with self.assertRaises(Exception) as ctx:
      add_two_numbers(-1, 5)
    self.assertEqual(str(ctx.exception), 'Numbers have to be positive')

  # Situation 4: a number exceeds 50 — should return 0
  def test_add_large_numbers(self):
    result = add_two_numbers(51, 3)
    self.assertEqual(result, 0)

  # Situation 5: both numbers at the boundary (exactly 50) — should return sum
  def test_add_boundary_numbers(self):
    result = add_two_numbers(50, 50)
    self.assertEqual(result, 100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(phone_number, password="testpass1", **kwargs):
    """Create a User with a bcrypt-hashed password."""
    defaults = {
        "first_name": "Test",
        "last_name": "User",
        "dob": "1990-01-01",
    }
    defaults.update(kwargs)
    return User.objects.create_user(
        phone_number=phone_number,
        password=hash_password(password),
        **defaults,
    )


def make_account(user, account_number, balance=Decimal("100000.00"), ifsc="IFSC0001"):
    return Account.objects.create(
        user=user,
        account_number=account_number,
        ifsc=ifsc,
        balance=balance,
    )


# ---------------------------------------------------------------------------
# SignupView tests  (POST /auth/signup/)
# ---------------------------------------------------------------------------

class SignupViewTest(APITestCase):

    def setUp(self):
        self.url = reverse("signup")

    def test_signup_success_returns_201_with_user_and_token(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1992-06-15",
            "phone_number": "9000000001",
            "password": "securepass",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["phone_number"], "9000000001")

    def test_signup_duplicate_phone_number_returns_400(self):
        make_user("9000000002")
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1993-07-20",
            "phone_number": "9000000002",
            "password": "securepass",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_missing_required_field_returns_400(self):
        # password is omitted
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1992-06-15",
            "phone_number": "9000000003",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LoginView tests  (POST /auth/login/)
# ---------------------------------------------------------------------------

class LoginViewTest(APITestCase):

    def setUp(self):
        self.url = reverse("login")
        self.raw_password = "mypassword"
        self.user = make_user("9100000001", password=self.raw_password)

    def test_login_success_returns_200_with_token(self):
        response = self.client.post(self.url, {
            "phone_number": "9100000001",
            "password": self.raw_password,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)

    def test_login_wrong_phone_number_returns_401(self):
        response = self.client.post(self.url, {
            "phone_number": "0000000000",
            "password": self.raw_password,
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_password_returns_401(self):
        response = self.client.post(self.url, {
            "phone_number": "9100000001",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# UserViewSet — set_default_account  (POST /users/<pk>/set-default-account/)
# ---------------------------------------------------------------------------

class SetDefaultAccountTest(APITestCase):

    def setUp(self):
        self.user = make_user("9200000001")
        self.account = make_account(self.user, "ACC_OWN_001")
        self.client.force_authenticate(user=self.user)

    def test_set_default_account_success(self):
        url = reverse("user-set-default-account", kwargs={"pk": self.user.pk})
        response = self.client.post(url, {"account": self.account.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.default_account_id, self.account.id)

    def test_set_default_account_belonging_to_other_user_returns_400(self):
        other_user = make_user("9200000002")
        other_account = make_account(other_user, "ACC_OTHER_001")
        url = reverse("user-set-default-account", kwargs={"pk": self.user.pk})
        response = self.client.post(url, {"account": other_account.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


# ---------------------------------------------------------------------------
# TransactionViewSet — create  (POST /transactions/)
# ---------------------------------------------------------------------------

class TransactionCreateTest(APITestCase):

    def setUp(self):
        self.sender = make_user("9300000001")
        self.receiver = make_user("9300000002")
        self.sender_account = make_account(self.sender, "SACC_001", balance=Decimal("200000.00"))
        self.receiver_account = make_account(self.receiver, "RACC_001", balance=Decimal("0.00"))
        self.receiver.default_account = self.receiver_account
        self.receiver.save()
        self.client.force_authenticate(user=self.sender)
        self.url = reverse("transaction-list")

    def _payload(self, **overrides):
        data = {
            "phone_number": "9300000002",
            "from_account": self.sender_account.id,
            "amount": "500.00",
            "category": Category.MISCELLANEOUS,
            "payment_method": PaymentMethod.UPI,
        }
        data.update(overrides)
        return data

    def test_create_transaction_success_returns_201(self):
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Transaction.Status.COMPLETED)

    def test_create_transaction_receiver_not_found_returns_400(self):
        response = self.client.post(self.url, self._payload(phone_number="0000000000"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No user found", response.data["error"])

    def test_create_transaction_receiver_has_no_default_account_returns_400(self):
        self.receiver.default_account = None
        self.receiver.save()
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no default account", response.data["error"])

    def test_create_transaction_budget_exceeded_returns_400(self):
        Budget.objects.create(
            user=self.sender,
            category=Category.MISCELLANEOUS,
            amount=Decimal("200.00"),
        )
        response = self.client.post(self.url, self._payload(amount="500.00"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Budget exceeded", response.data["error"])

    def test_create_transaction_basic_user_daily_limit_exceeded_returns_400(self):
        # Exhaust nearly all of the ₹50,000 daily limit with a past COMPLETED txn
        Transaction.objects.create(
            from_account=self.sender_account,
            to_account=self.receiver_account,
            amount=Decimal("49900.00"),
            category=Category.MISCELLANEOUS,
            payment_method=PaymentMethod.UPI,
            status=Transaction.Status.COMPLETED,
        )
        response = self.client.post(self.url, self._payload(amount="200.00"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Daily transfer limit exceeded", response.data["error"])

    def test_create_transaction_insufficient_balance_returns_400(self):
        self.sender_account.balance = Decimal("10.00")
        self.sender_account.save()
        response = self.client.post(self.url, self._payload(amount="500.00"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# TransactionViewSet — history  (GET /transactions/history/)
# ---------------------------------------------------------------------------

class TransactionHistoryTest(APITestCase):

    def setUp(self):
        self.user = make_user("9400000001")
        self.account = make_account(self.user, "HACC_001")
        self.client.force_authenticate(user=self.user)
        self.url = reverse("transaction-get-transaction-history-for-user")

    def test_missing_dates_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date and end_date is required", response.data["error"])

    def test_missing_end_date_returns_400(self):
        response = self.client.get(self.url, {"start_date": "2026-01-01"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_date_range_returns_200(self):
        response = self.client.get(self.url, {
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


# ---------------------------------------------------------------------------
# TransactionSummaryView  (GET /admin/transactions/summary/)
# ---------------------------------------------------------------------------

class TransactionSummaryViewTest(APITestCase):

    def setUp(self):
        self.admin_user = make_user(
            "9500000001",
            first_name="Admin",
            last_name="User",
            role=User.Role.ADMIN,
        )
        self.regular_user = make_user("9500000002")
        self.url = reverse("transaction-summary")

    def test_missing_date_param_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data["error"])

    def test_invalid_date_format_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url, {"date": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date format", response.data["error"])

    def test_future_date_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        future = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"date": future})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("future", response.data["error"])

    def test_valid_date_returns_200_with_summary(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url, {"date": date.today().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("transaction_count", response.data)
        self.assertIn("total_amount", response.data)

    def test_non_admin_user_gets_403(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.url, {"date": date.today().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

from .serializers import (
    AccountSerializer,
    BudgetSerializer,
    LoginSerializer,
    SetDefaultAccountSerializer,
    SignupSerializer,
    TransactionCreateSerializer,
    TransactionHistorySerializer,
    TransactionSerializer,
    UserSerializer,
)

# setup, after all, after each, before all, before each


class UserSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("9600000001", first_name="Alice", last_name="Brown")

    def test_contains_expected_fields(self):
        data = UserSerializer(self.user).data
        self.assertSetEqual(
            set(data.keys()),
            {"id", "first_name", "last_name", "dob", "phone_number", "default_account", "user_type"},
        )

    def test_values_match_user(self):
        data = UserSerializer(self.user).data
        self.assertEqual(data["phone_number"], "9600000001")
        self.assertEqual(data["first_name"], "Alice")
        self.assertEqual(data["last_name"], "Brown")
        self.assertEqual(data["user_type"], User.UserType.BASIC)
        self.assertIsNone(data["default_account"])

    def test_password_not_exposed(self):
        data = UserSerializer(self.user).data
        self.assertNotIn("password", data)


class SignupSerializerTest(TestCase):

    def _valid_data(self, **overrides):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "phone_number": "9610000001",
            "password": "strongpass",
        }
        data.update(overrides)
        return data

    def test_valid_data_is_valid(self):
        s = SignupSerializer(data=self._valid_data())
        self.assertTrue(s.is_valid(), s.errors)

    def test_password_shorter_than_8_chars_is_invalid(self):
        s = SignupSerializer(data=self._valid_data(password="short"))
        self.assertFalse(s.is_valid())
        self.assertIn("password", s.errors)

    def test_duplicate_phone_number_is_invalid(self):
        make_user("9610000002")
        s = SignupSerializer(data=self._valid_data(phone_number="9610000002"))
        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)

    def test_create_saves_user_and_hashes_password(self):
        s = SignupSerializer(data=self._valid_data(phone_number="9610000003"))
        self.assertTrue(s.is_valid())
        user = s.save()
        self.assertIsInstance(user, User)
        self.assertEqual(user.phone_number, "9610000003")
        # stored value must differ from the raw password
        self.assertNotEqual(user.password, "strongpass")

    def test_password_is_write_only(self):
        s = SignupSerializer(data=self._valid_data(phone_number="9610000004"))
        self.assertTrue(s.is_valid())
        self.assertNotIn("password", s.data)


class LoginSerializerTest(TestCase):

    def test_valid_data_is_valid(self):
        s = LoginSerializer(data={"phone_number": "9620000001", "password": "anypass"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_missing_password_is_invalid(self):
        s = LoginSerializer(data={"phone_number": "9620000001"})
        self.assertFalse(s.is_valid())
        self.assertIn("password", s.errors)

    def test_password_is_write_only(self):
        s = LoginSerializer(data={"phone_number": "9620000001", "password": "anypass"})
        self.assertTrue(s.is_valid())
        self.assertNotIn("password", s.data)


class SetDefaultAccountSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("9630000001")
        self.account = make_account(self.user, "SDAACC001")

    def test_valid_account_id_resolves_to_account_object(self):
        s = SetDefaultAccountSerializer(data={"account": self.account.id})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["account"], self.account)

    def test_nonexistent_account_id_is_invalid(self):
        s = SetDefaultAccountSerializer(data={"account": 9999999})
        self.assertFalse(s.is_valid())
        self.assertIn("account", s.errors)


class AccountSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("9640000001")
        self.account = make_account(self.user, "ACCACC001", balance=Decimal("5000.00"))

    def test_contains_expected_fields(self):
        data = AccountSerializer(self.account).data
        self.assertSetEqual(
            set(data.keys()),
            {"id", "user", "account_number", "ifsc", "balance", "account_type", "created_at"},
        )

    def test_values_match_account(self):
        data = AccountSerializer(self.account).data
        self.assertEqual(data["account_number"], "ACCACC001")
        self.assertEqual(Decimal(data["balance"]), Decimal("5000.00"))
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["account_type"], Account.AccountType.SAVINGS)

    def test_created_at_is_read_only(self):
        # Passing created_at in write data should be ignored, not cause an error
        s = AccountSerializer(data={
            "user": self.user.id,
            "account_number": "ACCACC002",
            "ifsc": "IFSC0001",
            "balance": "1000.00",
            "account_type": Account.AccountType.SAVINGS,
            "created_at": "2020-01-01T00:00:00Z",
        })
        self.assertTrue(s.is_valid(), s.errors)


class TransactionCreateSerializerTest(TestCase):

    def setUp(self):
        self.sender = make_user("9650000001")
        self.account = make_account(self.sender, "TCSACC001")

    def _valid_data(self, **overrides):
        data = {
            "phone_number": "9650000002",
            "from_account": self.account.id,
            "amount": "500.00",
            "category": Category.HOUSEHOLD,
            "payment_method": PaymentMethod.UPI,
        }
        data.update(overrides)
        return data

    def test_valid_data_is_valid(self):
        s = TransactionCreateSerializer(data=self._valid_data())
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_category_is_invalid(self):
        s = TransactionCreateSerializer(data=self._valid_data(category="INVALID"))
        self.assertFalse(s.is_valid())
        self.assertIn("category", s.errors)

    def test_invalid_payment_method_is_invalid(self):
        s = TransactionCreateSerializer(data=self._valid_data(payment_method="CASH"))
        self.assertFalse(s.is_valid())
        self.assertIn("payment_method", s.errors)

    def test_description_defaults_to_empty_string(self):
        s = TransactionCreateSerializer(data=self._valid_data())
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["description"], "")

    def test_nonexistent_from_account_is_invalid(self):
        s = TransactionCreateSerializer(data=self._valid_data(from_account=999999))
        self.assertFalse(s.is_valid())
        self.assertIn("from_account", s.errors)

    def test_all_valid_categories_are_accepted(self):
        for cat in Category.values:
            s = TransactionCreateSerializer(data=self._valid_data(category=cat))
            self.assertTrue(s.is_valid(), f"Category '{cat}' should be valid but got: {s.errors}")

    def test_all_valid_payment_methods_are_accepted(self):
        for method in PaymentMethod.values:
            s = TransactionCreateSerializer(data=self._valid_data(payment_method=method))
            self.assertTrue(s.is_valid(), f"PaymentMethod '{method}' should be valid but got: {s.errors}")


class TransactionSerializerTest(TestCase):

    def setUp(self):
        self.sender = make_user("9660000001")
        self.receiver = make_user("9660000002")
        self.sender_account = make_account(self.sender, "TSACC001", balance=Decimal("10000.00"))
        self.receiver_account = make_account(self.receiver, "TSACC002")
        self.txn = Transaction.objects.create(
            from_account=self.sender_account,
            to_account=self.receiver_account,
            amount=Decimal("500.00"),
            category=Category.TRAVEL,
            payment_method=PaymentMethod.UPI,
            status=Transaction.Status.COMPLETED,
        )

    def test_contains_expected_fields(self):
        data = TransactionSerializer(self.txn).data
        self.assertSetEqual(
            set(data.keys()),
            {"id", "from_account", "to_account", "amount", "category",
             "description", "payment_method", "status", "created_at"},
        )

    def test_values_match_transaction(self):
        data = TransactionSerializer(self.txn).data
        self.assertEqual(Decimal(data["amount"]), Decimal("500.00"))
        self.assertEqual(data["status"], Transaction.Status.COMPLETED)
        self.assertEqual(data["category"], Category.TRAVEL)
        self.assertEqual(data["payment_method"], PaymentMethod.UPI)


class TransactionHistorySerializerTest(TestCase):

    def setUp(self):
        self.sender = make_user("9670000001", first_name="Bob", last_name="Smith")
        self.receiver = make_user("9670000002", first_name="Carol", last_name="Jones")
        self.sender_account = make_account(self.sender, "THISACC001", balance=Decimal("10000.00"))
        self.receiver_account = make_account(self.receiver, "THISACC002")
        self.txn = Transaction.objects.create(
            from_account=self.sender_account,
            to_account=self.receiver_account,
            amount=Decimal("300.00"),
            category=Category.LEISURE,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=Transaction.Status.COMPLETED,
        )

    def test_contains_expected_fields(self):
        data = TransactionHistorySerializer(self.txn, context={"user_account_ids": set()}).data
        self.assertSetEqual(
            set(data.keys()),
            {"txn_id", "receiver_name", "receiver_account_number", "txn_date", "amount", "status", "txn_type"},
        )

    def test_txn_type_is_debit_when_from_account_belongs_to_user(self):
        data = TransactionHistorySerializer(
            self.txn, context={"user_account_ids": {self.sender_account.id}}
        ).data
        self.assertEqual(data["txn_type"], "DEBIT")

    def test_txn_type_is_credit_when_to_account_belongs_to_user(self):
        data = TransactionHistorySerializer(
            self.txn, context={"user_account_ids": {self.receiver_account.id}}
        ).data
        self.assertEqual(data["txn_type"], "CREDIT")

    def test_receiver_name_is_full_name_of_to_account_owner(self):
        data = TransactionHistorySerializer(self.txn, context={}).data
        self.assertEqual(data["receiver_name"], "Carol Jones")

    def test_receiver_account_number_matches_to_account(self):
        data = TransactionHistorySerializer(self.txn, context={}).data
        self.assertEqual(data["receiver_account_number"], "THISACC002")


class BudgetSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("9680000001")
        self.budget = Budget.objects.create(
            user=self.user,
            category=Category.HOUSEHOLD,
            amount=Decimal("5000.00"),
        )

    def test_contains_expected_fields(self):
        data = BudgetSerializer(self.budget).data
        self.assertSetEqual(set(data.keys()), {"id", "user", "category", "amount"})

    def test_values_match_budget(self):
        data = BudgetSerializer(self.budget).data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["category"], Category.HOUSEHOLD)
        self.assertEqual(Decimal(data["amount"]), Decimal("5000.00"))

    def test_valid_data_is_valid(self):
        s = BudgetSerializer(data={
            "user": self.user.id,
            "category": Category.LEISURE,
            "amount": "1000.00",
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_category_is_invalid(self):
        s = BudgetSerializer(data={
            "user": self.user.id,
            "category": "FOOD",
            "amount": "1000.00",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("category", s.errors)


# ---------------------------------------------------------------------------
# UserManager.create_superuser tests
# ---------------------------------------------------------------------------

class UserManagerCreateSuperuserTest(TestCase):

    def test_create_superuser_returns_a_user_instance(self):
        user = User.objects.create_superuser(
            phone_number="9700000001",
            password=hash_password("adminpass"),
            first_name="Super",
            last_name="User",
            dob="1985-01-01",
        )
        self.assertIsInstance(user, User)
        self.assertEqual(user.phone_number, "9700000001")

    def test_create_superuser_sets_is_active_true_by_default(self):
        user = User.objects.create_superuser(
            phone_number="9700000002",
            password=hash_password("adminpass"),
            first_name="Super",
            last_name="User",
            dob="1985-01-01",
        )
        self.assertTrue(user.is_active)

    def test_create_superuser_respects_explicit_is_active_false(self):
        # setdefault only applies when is_active is NOT passed —
        # if caller explicitly passes is_active=False it must be honoured
        user = User.objects.create_superuser(
            phone_number="9700000003",
            password=hash_password("adminpass"),
            first_name="Super",
            last_name="User",
            dob="1985-01-01",
            is_active=False,
        )
        self.assertFalse(user.is_active)

    def test_create_superuser_persists_to_database(self):
        User.objects.create_superuser(
            phone_number="9700000004",
            password=hash_password("adminpass"),
            first_name="Super",
            last_name="User",
            dob="1985-01-01",
        )
        self.assertTrue(User.objects.filter(phone_number="9700000004").exists())
