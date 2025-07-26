from rest_framework import serializers
from booking.models import Question


class AdminQuestionBaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = "__all__"

    def validate(self, data):
        data = super().validate(data)
        event = self.instance.event if self.instance else data.get("event")
        products = data.get("products") or (self.instance.products if self.instance else None)
        if products and event:
            # Check if the products belong to the same event
            for product in products:
                if product.event != event:
                    raise serializers.ValidationError(
                        "Products must belong to the same event"
                    )
        return data


class AdminQuestionDetailSerializer(serializers.ModelSerializer):
    products = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = Question
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = [
            "products",
            "all_products",
            "hidden",
        ]
