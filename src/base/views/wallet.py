from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from base.models import User, Wallet, WalletTransaction
from base.serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    WalletUpdateSerializer,
)
from base.helpers.api_permissions import AdminPermission, LoggedIn
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from base.filters.wallet import WalletTransactionFilter


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for WalletTransaction for the current user.
    Can only list transactions for the user with filters, ordering and pagination.
    Optionally admin users can list transactions for all users and can filter by wallet.
    """

    permission_classes = [LoggedIn]
    filter_backends = [DjangoFilterBackend]
    serializer_class = WalletTransactionSerializer
    filterset_class = WalletTransactionFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WalletTransaction.objects.none()
        if self.request.user.is_staff:
            return WalletTransaction.objects.all()
        return WalletTransaction.objects.filter(wallet__user=self.request.user)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "to_wallet_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: WalletTransactionSerializer()},
    )
    @action(detail=False, methods=["post"], permission_classes=[LoggedIn])
    def transfer(self, request):
        """
        Transfer money from one wallet to another.
        """
        to_wallet_id = request.data.get("to_wallet_id")
        amount = request.data.get("amount")
        description = request.data.get("description")
        from_wallet = Wallet.get_wallet_for_user(request.user)
        try:
            from_trans, to_trans = Wallet.transfer(
                from_wallet.id, to_wallet_id, amount, description
            )
            return Response(WalletTransactionSerializer(from_trans).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WalletAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [AdminPermission]

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    def get_serializer_class(self):
        if self.action == "update" or self.action == "partial_update":
            return WalletUpdateSerializer
        return WalletSerializer

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: WalletTransactionSerializer()},
    )
    @action(detail=True, methods=["post"], permission_classes=[AdminPermission])
    def credit(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get("amount")
        description = request.data.get("description")
        trans = wallet.credit(amount, description)
        return Response(WalletTransactionSerializer(trans).data)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: WalletTransactionSerializer()},
    )
    @action(detail=True, methods=["post"], permission_classes=[AdminPermission])
    def debit(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get("amount")
        description = request.data.get("description")
        trans = wallet.debit(amount, description)
        return Response(WalletTransactionSerializer(trans).data)
