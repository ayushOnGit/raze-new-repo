from rest_framework import viewsets, serializers, filters
from django_filters.rest_framework import DjangoFilterBackend
from booking.models import (
    Promotion,
    Quota,
    Product,
)
from booking.serializers.promotion import (
    AdminPromotionSerializer,
    AdminPromotionDetailSerializer,
    OwnerPromotionSerializer,
    OwnerPromotionDetailSerializer,
    ProductPromotionSerializer,
)
from base.helpers.api_permissions import AdminPermission, LoggedIn
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status


class AdminPromotionViewSet(viewsets.ModelViewSet):
    """
    Admin users can see all promotions and perform all CRUD operations.
    """

    queryset = Promotion.objects.all()
    serializer_class = AdminPromotionSerializer
    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "event",
        "all_products",
        "code",
        "is_active",
        "priority",
        "applicable_user_type",
        "promo_owner",
    ]
    ordering_fields = ["priority", "created_on"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminPromotionDetailSerializer
        return AdminPromotionSerializer


class OwnerPromotionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Owners can see their promotions but not create or modify them.
    """

    serializer_class = OwnerPromotionSerializer
    permission_classes = [LoggedIn]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event"]
    ordering_fields = ["created_on"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OwnerPromotionDetailSerializer
        return OwnerPromotionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Promotion.objects.none()
        return Promotion.objects.filter(promo_owner=self.request.user, is_active=True)


class ProductPromotionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductPromotionSerializer
    permission_classes = [LoggedIn]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "applicable_user_type"]
    ordering_fields = ["priority"]

    def get_queryset(self):
        return Promotion.get_listing_qs()

    def list(self, request, *args, **kwargs):
        # Make sure event is provided in the query params
        event_id = request.query_params.get("event")
        if not event_id:
            return Response(
                {"detail": "Event ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "product",
                openapi.IN_QUERY,
                description="Product ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of promotions",
                schema=ProductPromotionSerializer(many=True),
            )
        },
    )
    @action(detail=False, methods=["get"])
    def for_product(self, request, *args, **kwargs):
        product_id = request.query_params.get("product")
        if not product_id:
            return Response(
                {"detail": "Product ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND
            )

        promotions = Promotion.list_for_product(product)
        serializer = self.get_serializer(promotions, many=True)
        return Response(serializer.data)
