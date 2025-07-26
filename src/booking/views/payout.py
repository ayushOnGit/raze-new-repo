from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from base.models import Wallet
from booking.models import WalletPayout
from booking.serializers.payout import (
    WalletPayoutSerializer,
    WalletPayoutAdminSerializer,
)
from base.helpers.api_permissions import LoggedIn


class WalletPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for WalletPayout for the current user.
    Can only list payouts for the user with filters, ordering and pagination.
    Optionally admin users can list payouts for all users.
    """

    permission_classes = [LoggedIn]
    serializer_class = WalletPayoutSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "wallet"]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return WalletPayoutAdminSerializer
        return WalletPayoutSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WalletPayout.objects.none()
        if self.request.user.is_staff:
            return WalletPayout.objects.all()
        return WalletPayout.objects.filter(wallet__user=self.request.user)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "description": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: WalletPayoutSerializer()},
    )
    @action(detail=False, methods=["post"], permission_classes=[LoggedIn])
    def initiate(self, request):
        """
        Request a payout from the wallet.
        """
        description = request.data.get("description")
        try:
            wallet = Wallet.get_wallet_for_user(request.user)
            wallet = Wallet.lock_wallet(wallet.wallet_id)
            amount = wallet.balance
            ref_id = ""  # todo: generate ref id here.
            payment_gateway = ""
            payment_link = ""
            payout = WalletPayout.initiate(
                wallet,
                amount,
                ref_id,
                payment_gateway,
                payment_link=payment_link,
                description=description,
                is_locked=True,
            )
            return Response(WalletPayoutSerializer(payout).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
