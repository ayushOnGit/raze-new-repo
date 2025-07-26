from rest_framework import viewsets, serializers, filters
from django_filters.rest_framework import DjangoFilterBackend
from booking.models import (
    Product,
    Quota,
)
from booking.serializers.product import (
    ProductSerializer,
    AdminProductDetailSerializer,
    QuotaSerializer,
)
from base.helpers.api_permissions import AdminPermission


class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "section", "is_active", "name", "subevent"]
    ordering_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminProductDetailSerializer
        return ProductSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "subevent"]
    ordering_fields = ["name"]

    def get_serializer_class(self):
        return ProductSerializer


class AdminQuotaViewSet(viewsets.ModelViewSet):
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
    permission_classes = [AdminPermission]
