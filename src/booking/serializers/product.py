from rest_framework import serializers
from booking.models import (
    Product,
    Quota,
)


class QuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quota
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    is_sale_active = serializers.SerializerMethodField()

    class Meta:
        model = Product
        exclude = ("sale_start", "sale_end", "is_active", "tickets_active_until")

    def get_is_sale_active(self, obj):
        return obj.is_sale_active()

    def validate(self, attrs):
        product = self.instance
        event = product.event if product else attrs.get("event")
        if event and attrs.get("section"):
            section = attrs["section"]
            if not event.layout:
                raise serializers.ValidationError(
                    "Event must have a layout to assign sections"
                )
            if section.layout.layout_id != event.layout.layout_id:
                raise serializers.ValidationError(
                    "Section must belong to the same layout as the event"
                )
        if event and attrs.get("subevent"):
            subevent = attrs["subevent"]
            if subevent.event.event_id != event.event_id:
                raise serializers.ValidationError(
                    "Subevent must belong to the same event"
                )
        return super().validate(attrs)


class AdminProductDetailSerializer(ProductSerializer):
    quotas = QuotaSerializer(many=True)

    class Meta:
        model = Product
        fields = "__all__"
