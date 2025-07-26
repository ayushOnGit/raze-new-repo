from rest_framework import serializers
from base.models import WalletTransaction
from base.serializers import WalletTransactionSerializer
from booking.models import WalletPayout


class WalletPayoutSerializer(serializers.ModelSerializer):
    """
    Serializer for a wallet payout.
    """

    debit_transaction = WalletTransactionSerializer(read_only=True)

    class Meta:
        model = WalletPayout
        fields = [
            "payout_id",
            "wallet",
            "amount",
            "timestamp",
            "status",
            "debit_transaction",
            "description",
            "payment_link",
        ]


class WalletPayoutAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for a wallet payout with all fields.
    """

    debit_transaction = WalletTransactionSerializer(read_only=True)

    class Meta:
        model = WalletPayout
        fields = [
            "payout_id",
            "wallet",
            "amount",
            "timestamp",
            "status",
            "debit_transaction",
            "description",
            "reference_id",
            "payment_gateway",
            "payment_link",
        ]
