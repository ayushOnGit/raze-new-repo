from rest_framework import serializers
from booking.models import (
    Promotion,
    Quota,
)
from .product import ProductSerializer, QuotaSerializer


class AdminPromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"


class AdminPromotionDetailSerializer(AdminPromotionSerializer):
    products = ProductSerializer(many=True)
    quota = QuotaSerializer()


OWNER_FILEDS = [
            "promo_id",
            "name",
            "description",
            "code",
            "is_active",
            "discount_percentage",
            "discount_fixed",
            "max_discount",
            "min_order_value",
            "max_order_value",
            "min_quantity",
            "max_quantity",
            "quantity_step",
        ]

class OwnerPromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = OWNER_FILEDS


class OwnerPromotionDetailSerializer(OwnerPromotionSerializer):
    products = ProductSerializer(many=True)
    quota = QuotaSerializer()

    class Meta:
        model = Promotion
        fields = OWNER_FILEDS + ["products", "quota"]

class ProductPromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ["promo_id", "name", "description", "applicable_user_type"]
