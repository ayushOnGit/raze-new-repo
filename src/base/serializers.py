from rest_framework import serializers
from base.models import User, Wallet, WalletTransaction, OTP
from .auth import NativeAuthentication
from .helpers.phone_number import validate_phone_number


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving self-account details"""

    class Meta:
        model = User
        fields = [
            "user_id",
            "name",
            "email",
            "phone_number",
            "date_joined",
            "birthdate",
            "is_onboarded",
            "profile_picture",
            "is_email_verified",
            "allow_app_notification",
        ]


class UserSerializer(serializers.ModelSerializer):
    "User serializer for admin view"

    class Meta:
        model = User
        fields = "__all__"


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating name and birthdate"""

    birthdate = serializers.DateField(
        required=False
    )

    class Meta:
        model = User
        fields = ["name", "birthdate", "email", "profile_picture", "allow_app_notification"]


class WalletSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = ["wallet_id", "user", "balance", "can_receive_payments"]
        read_only_fields = ["wallet_id", "balance"]


class WalletTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = WalletTransaction
        fields = ["transaction_id", "wallet", "amount", "timestamp", "description"]


class WalletUpdateSerializer(serializers.ModelSerializer):
    """
    Only allow editing the can_receive_payments field
    """

    class Meta:
        model = Wallet
        fields = ["can_receive_payments"]


class OTPSerializer(serializers.Serializer):
    """
    Serializer for OTP
    """

    class Meta:
        model = OTP
        fields = "__all__"

    def validate_phone_number(self, value):
        """
        Validate the phone number format
        """
        try:
            validate_phone_number(value)
        except serializers.ValidationError:
            raise serializers.ValidationError("Invalid phone number format")
        return value

    def validate_otp(self, value):
        """
        Validate the OTP format
        """
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("OTP must be a 6-digit number")
        return value
