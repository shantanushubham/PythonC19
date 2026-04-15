from datetime import date, timedelta
from django.utils import timezone

from django.db import transaction as db_transaction
from django.db.models import Q, Sum as models_sum, Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from users.jwt_util import generate_token

from .bcrypt_util import verify_password
from .models import Account, Budget, Transaction, User
from .payment import get_payment_processor
from .permissions import IsAdminUser
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


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=["post"], url_path="set-default-account")
    def set_default_account(self, request, pk=None):
        user = self.get_object()
        serializer = SetDefaultAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.validated_data["account"]
        if account.user_id != user.id:
            return Response(
                {"error": "That account does not belong to this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.default_account = account
        user.save(update_fields=["default_account"])
        return Response(UserSerializer(user).data)


class AccountViewSet(ModelViewSet):
    # This is allowing the ModelViewSet to perform a JOIN on user and account table
    queryset = Account.objects.select_related("user").all()
    serializer_class = AccountSerializer


class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.select_related("from_account", "to_account").all()
    serializer_class = TransactionSerializer

    def create(self, request, *args, **kwargs):
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Step 1: Resolve to_account via phone_number
        try:
            # SELCT * FROM users WHERE phone_number=<phone_number>
            receiver = User.objects.get(phone_number=data["phone_number"])
        except User.DoesNotExist:
            return Response(
                {"error": "No user found with the given phone number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        to_account = receiver.default_account
        if to_account is None:  # null = None
            return Response(
                {"error": "Receiver has no default account configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 2: from_account already resolved by serializer
        from_account = data["from_account"]

        # Step 3: Get payment processor
        try:
            processor = get_payment_processor(data["payment_method"])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Budget check for this category this month
        today = date.today()
        budget = Budget.objects.filter(
            user=from_account.user, category=data["category"]
        ).first()

        # Budget Found
        if budget is not None:
            f"""
            Checking with following WHERE clause
            1. from_account (Account) but from_account__user (Account's User)

            SELECT * FROM transactions WHERE
                from_account.user = <from_account.user>
            AND category = <category>
            AND created_at.year = <year>
            AND created_at.month = <month>
            AND status = "COMPLETED"
            """
            monthly_transactions = Transaction.objects.filter(
                from_account__user=from_account.user,
                category=data["category"],
                created_at__year=today.year,
                created_at__month=today.month,
                status=Transaction.Status.COMPLETED,
            )

            month_spent = monthly_transactions.aggregate(total=models_sum("amount"))
            if month_spent["total"] is None:
                month_spent = 0
            else:
                month_spent = month_spent["total"]

            if month_spent + data["amount"] > budget.amount:
                return Response(
                    {
                        "error": (
                            f"Budget exceeded for category '{data['category']}'. "
                            f"Budget: ₹{budget.amount}, Spent so far: ₹{month_spent}, "
                            f"Requested: ₹{data['amount']}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Step 5: Enforce daily send limit for BASIC_USER
        sender = from_account.user
        if sender.user_type == User.UserType.BASIC:
            window_start = timezone.now() - timedelta(hours=24)
            sent_in_window = Transaction.objects.filter(
                from_account__user=sender,
                created_at__gte=window_start,
                status=Transaction.Status.COMPLETED,
            ).aggregate(total=models_sum("amount"))["total"] or 0

            if sent_in_window + data["amount"] > User.BASIC_DAILY_LIMIT:
                return Response(
                    {
                        "error": (
                            f"Daily transfer limit exceeded. "
                            f"BASIC_USER limit: ₹{User.BASIC_DAILY_LIMIT:,} per 24 hours. "
                            f"Sent so far: ₹{sent_in_window:,}, Requested: ₹{data['amount']}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Step 6: Process payment atomically
        try:
            with db_transaction.atomic():
                processor.pay(data["amount"], from_account, to_account)
                txn = Transaction.objects.create(
                    from_account=from_account,
                    to_account=to_account,
                    amount=data["amount"],
                    category=data["category"],
                    description=data.get("description", ""),
                    payment_method=data["payment_method"],
                    status=Transaction.Status.COMPLETED,
                )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["GET"], url_path="history")
    def get_transaction_history_for_user(self, request: Request):
        # Verify JWT Token
        user_id = request.user.id
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        """
            In order to get all transactions for a user, we need to identify all accounts of a user
        """
        # [1, 2]
        user_accounts: list = Account.objects.filter(user_id=user_id).values_list(
            "id", flat=True
        )

        transactions = Transaction.objects.filter(
            Q(from_account__in=user_accounts) | Q(to_account__in=user_accounts),
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).select_related("from_account", "to_account__user")

        user_account_ids = set(user_accounts)

        serializer = TransactionHistorySerializer(
            transactions, many=True, context={"user_account_ids": user_account_ids}
        )
        return Response(serializer.data)


class BudgetViewSet(ModelViewSet):
    queryset = Budget.objects.select_related("user").all()
    serializer_class = BudgetSerializer


class SignupView(APIView):
    authentication_classes = []
    # TODO: Revisit later
    permission_classes = []

    def post(self, request: Request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        jwt_token = generate_token(user)
        return Response(
            {"user": UserSerializer(user).data, "token": jwt_token}, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid phone number or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_password(password, user.password):
            return Response(
                {"error": "Invalid phone number or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        jwt_token = generate_token(user)
        return Response(
            {"user": UserSerializer(user).data, "token": jwt_token},
            status=status.HTTP_200_OK,
        )


class TransactionSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request: Request):
        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {"error": "Query parameter 'date' is required (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            query_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()

        if query_date > today:
            return Response(
                {"error": "Date cannot be in the future."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if query_date == today:
            # Only count transactions up to right now
            qs = Transaction.objects.filter(
                created_at__date=today,
                created_at__lte=timezone.now(),
            )
        else:
            qs = Transaction.objects.filter(created_at__date=query_date)

        result = qs.aggregate(
            total_amount=models_sum("amount"),
            total_count=Count("id"),
        )

        return Response(
            {
                "date": date_str,
                "transaction_count": result["total_count"] or 0,
                "total_amount": result["total_amount"] or 0,
            },
            status=status.HTTP_200_OK,
        )
