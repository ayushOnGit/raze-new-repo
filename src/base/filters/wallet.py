import django_filters
from base.models import User, Wallet, WalletTransaction


class WalletTransactionFilter(django_filters.FilterSet):
    timestamp__gte = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="gte"
    )  # Greater than
    timestamp__lte = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="lte"
    )  # Less than

    wallet = django_filters.NumberFilter(field_name="wallet")

    class Meta:
        model = WalletTransaction
        fields = ["wallet", "timestamp__gte", "timestamp__lte", "transaction_type"]
