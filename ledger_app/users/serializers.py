from rest_framework import serializers

from .bcrypt_util import hash_password
from .models import Account, Budget, Category, PaymentMethod, Transaction, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "dob",
            "phone_number",
            "default_account",
            "user_type",
        ]


class SignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    dob = serializers.DateField()
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        raw_password = validated_data.pop("password")
        return User.objects.create_user(password=hash_password(raw_password), **validated_data)


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)


class SetDefaultAccountSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "user",
            "account_number",
            "ifsc",
            "balance",
            "account_type",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class TransactionCreateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    from_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.ChoiceField(choices=Category.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "from_account",
            "to_account",
            "amount",
            "category",
            "description",
            "payment_method",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TransactionHistorySerializer(serializers.ModelSerializer):
    txn_id = serializers.UUIDField(source="id")
    receiver_name = serializers.SerializerMethodField() # Depends on a return value of a fucntion that the developer will write
    receiver_account_number = serializers.CharField(source="to_account.account_number")
    txn_date = serializers.DateTimeField(source="created_at")
    txn_type = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ["txn_id", "receiver_name", "receiver_account_number", "txn_date", "amount", "status", "txn_type"]

    def get_receiver_name(self, obj):
        return str(obj.to_account.user)

    def get_txn_type(self, obj):
        user_account_ids = self.context.get("user_account_ids", set())
        if obj.from_account_id in user_account_ids:
            return "DEBIT"
        else:
            return "CREDIT"

   


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ["id", "user", "category", "amount"]
        read_only_fields = ["id"]
