from rest_framework import serializers
from booking.models import Cart, Order, Ticket, Answer
from .product import ProductSerializer
from .event import EventBaseSerializer
from .question import QuestionSerializer


class AnswerDetailSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = "__all__"


class AnswerSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), required=False, allow_null=True, default=None
    )
    cart = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(), required=False, allow_null=True, default=None
    )

    class Meta:
        model = Answer
        fields = "__all__"

    """
    Validate the cart or order is owned by the current user. And either cart or order is provided.
    """

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.is_authenticated:
            raise serializers.ValidationError("User is not authenticated")

        answer = self.instance
        cart = attrs.get("cart", answer.cart if answer else None)
        order = attrs.get("order", answer.order if answer else None)
        question = attrs.get("question", answer.question if answer else None)
        if not cart and not order:
            raise serializers.ValidationError("Either cart or order must be provided")

        if question and not question.can_modify_later and order:
            raise serializers.ValidationError(
                "This answer cannot modified after order creation"
            )

        # Make sure the question is applicable to cart or order product
        target_product = cart.product if (cart and cart.product) else order.product
        if not question.is_applicable(target_product):
            raise serializers.ValidationError(
                "Question is not applicable to this product"
            )
        target_user = cart.user if cart else order.user
        if target_user.user_id != user.user_id:
            raise serializers.ValidationError("User does not own the cart or order")

        # Validate the answer for this question
        if attrs.get("answer"):
            answer = attrs["answer"]
            attrs["answer"] = question.clean_answer(answer)
        return super().validate(attrs)


class CartSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "cart_id",
            "user",
            "discount_coupon",
            "expires_on",
            "gross_price",
            "tax",
            "platform_fee",
            "discount_amount",
            "net_price",
            "status",
            "product",
            "quantity",
            "is_promoter",
            "end_user_discount_percentage",
            "payment_mode",
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity should be greater than 0")
        return value


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_id",
            "user",
            "timestamp",
            "expiry_on",
            "gross_price",
            "tax",
            "platform_fee",
            "discount_amount",
            "net_price",
            "discount_coupon",
            "payment_id",
            "status",
            "failure_reason",
            "product",
            "quantity",
        ]


class TicketSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.order_id")
    user_id = serializers.IntegerField(source="user.user_id")
    product = ProductSerializer(source="product", read_only=True)
    event = EventBaseSerializer(source="product.event", read_only=True)

    class Meta:
        model = Ticket
        fields = ["ticket_id", "order_id", "user", "is_cancelled", "product"]
