from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction
from booking.models import Cart, Order, Ticket, Product, Answer
from booking.serializers.order import (
    CartSerializer,
    OrderSerializer,
    TicketSerializer,
    AnswerSerializer,
    AnswerDetailSerializer,
)
from booking.serializers.question import QuestionSerializer
from base.helpers.api_permissions import AdminPermission
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from booking.services.order import CartService, OrderService
from rest_framework.parsers import FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend

# User APIs


class AnswerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AnswerSerializer
    parser_classes = (FormParser, MultiPartParser)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["cart", "order"]
    http_method_names = ["get", "post", "patch", "delete"]
    queryset = Answer.objects.none()

    def get_queryset(self):
        """
        Get answers for the logged in user.
        """
        if getattr(self, "swagger_fake_view", False):
            return Answer.objects.none()
        queryset = Answer.objects.all()
        queryset = queryset.filter(cart__user=self.request.user) | queryset.filter(
            order__user=self.request.user
        )
        return queryset

    def get_serializer_class(self):
        """
        Return AnswerDetailSerializer for retrieve action.
        Return AnswerSerializer for all other actions.
        """
        if self.action == "retrieve":
            return AnswerDetailSerializer
        return AnswerSerializer

    """
    Custom patch method to disallow changing question, cart or order.
    """

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Make sure question, cart or order is not changed
        question = serializer.validated_data.get("question", instance.question)
        cart = serializer.validated_data.get("cart", instance.cart)
        order = serializer.validated_data.get("order", instance.order)
        if (
            question != instance.question
            or cart != instance.cart
            or order != instance.order
        ):
            raise ValidationError("Cannot change question, cart or order.")
        self.perform_update(serializer)
        return Response(serializer.data)

    """
    Custom delete method to disallow deleting answer if order is created and can_modify_later is False.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if (
            instance.question
            and not instance.question.can_modify_later
            and instance.order
        ):
            raise ValidationError("Cannot delete answer after order creation.")
        # Dont allow delete if the question is marked as required and the answer is linked to an order.
        if instance.question and instance.question.required and instance.order:
            raise ValidationError("Cannot delete answer for required question.")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        carts = Cart.objects.filter(user=request.user)
        return Response(CartSerializer(carts, many=True).data)

    def retrieve(self, request, pk=None):
        cart = get_object_or_404(Cart, pk=pk, user=request.user)
        return Response(CartSerializer(cart).data)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "product_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "quantity": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
                "is_promoter": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    default=False,
                    description="Set True for Circle flow.",
                ),
            },
        ),
        responses={200: CartSerializer()},
    )
    @action(detail=False, methods=["post"])
    def create_cart(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)
        is_promoter = request.data.get("is_promoter", False)

        product = get_object_or_404(Product, pk=product_id)
        try:
            cart = Cart.create_cart(request.user, product, quantity, is_promoter)
            return Response(CartSerializer(cart).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "quantity": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
            },
        ),
        responses={200: CartSerializer()},
    )
    @action(detail=True, methods=["post"])
    def update_quanity(self, request, pk=None):
        quantity = request.data.get("quantity", 1)

        cart_service = CartService(request.user)
        try:
            cart = cart_service.change_quantity(pk, quantity)
            return Response(CartSerializer(cart).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "payment_mode": openapi.Schema(
                    type=openapi.TYPE_STRING, default="online"
                ),
            },
        ),
        responses={200: CartSerializer()},
    )
    @action(detail=True, methods=["post"])
    def change_payment_mode(self, request, pk=None):
        """
        "online" for razorpay payment gateway.
        "wallet" for wallet payment.
        """
        payment_mode = request.data.get("payment_mode")

        cart_service = CartService(request.user)
        try:
            cart = cart_service.change_payment_mode(pk, payment_mode)
            return Response(CartSerializer(cart).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def delete(self, request, pk=None):
        cart_service = CartService(request.user)
        try:
            cart_service.cancel_cart(pk)
            return Response(
                {"message": "Cart deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="get",
        responses={200: QuestionSerializer()},
    )
    @action(detail=True, methods=["get"])
    def get_questions(self, request, pk=None):
        """
        Get questions for the cart.
        """
        cart = get_object_or_404(Cart, pk=pk, user=request.user)
        questions = cart.get_questions()
        return Response(QuestionSerializer(questions, many=True).data)


class OrderViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List all orders for the logged in user.
        """
        orders = Order.objects.filter(user=request.user)
        return Response(OrderSerializer(orders, many=True).data)

    def retrieve(self, request, pk=None):
        """
        Get details of a specific order of the logged in user only.
        """
        order = get_object_or_404(Order, pk=pk, user=request.user)
        return Response(OrderSerializer(order).data)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"cart_id": openapi.Schema(type=openapi.TYPE_INTEGER)},
        ),
        responses={200: OrderSerializer()},
        operation_summary="Create order from cart.",
    )
    @action(detail=False, methods=["post"])
    def create_from_cart(self, request):
        """
        New order will be either in "initial" or "successfull" state.
        If in initial state, user needs to confirm the payment to mark it as successfull.
        Orders expire after a certain time if not confirmed.
        """
        cart_id = request.data.get("cart_id")
        order_service = OrderService(request.user)
        try:
            order = order_service.create_order(cart_id)
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
        responses={200: OrderSerializer()},
    )
    @action(detail=False, methods=["post"])
    def wallet_recharge(self, request):
        """
        Create a wallet recharge order for the user.
        This does not create any tickets, only adds the amount to the wallet. No cart is required for this.
        """
        amount = request.data.get("amount")
        order_service = OrderService(request.user)
        try:
            # Validate amount input type
            if not isinstance(amount, (int, float)):
                raise ValidationError("Amount should be a number.")

            order = order_service.create_recharge_order(amount)
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"payment_info": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={200: OrderSerializer()},
        operation_summary="Final step in order flow to confirm the payment for the order",
        operation_description="""
        Confirm the payment for the order to mark it as successful. Tickets will be generated after payment confirmation. 
        payment_info: JSON encoded string containing payment information from client.
        For razorpay payment gateway, the payment_info should be in the following format:
        {
            "razorpay_payment_id": "pay_1Iv3c3K1hjB2Gv",
            "razorpay_order_id": "order_1Iv3c3K1hjB2Gv", // razorpay_order_id should be same as payment_id in order object.
            "razorpay_signature": "f5d8a5b9a7d6f5b7f6d5a7"
        }
        """,
    )
    @action(detail=True, methods=["post"])
    def confirm_payment(self, request, pk=None):
        payment_info = request.data.get("payment_info")

        order_service = OrderService(request.user)
        try:
            order = order_service.confirm_payment(pk, payment_info)
            return Response(OrderSerializer(order).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING, default="User request"
                )
            },
        ),
        responses={200: OrderSerializer()},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cannot cancel an order if it is already in "successfull" state.
        """
        order = get_object_or_404(Order, pk=pk, user=request.user)
        reason = request.data.get("reason", "User request")

        with transaction.atomic():
            try:
                order.cancel_order(reason)
                return Response(OrderSerializer(order).data)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TicketViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Only shows active tickets for the logged in user.
        """
        tickets = Ticket.get_active_qs().filter(user=request.user)
        return Response(TicketSerializer(tickets, many=True).data)


# Admin APIs
class AdminOrderViewSet(viewsets.ViewSet):
    permission_classes = [AdminPermission]

    def list(self, request):
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)

    def retrieve(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        return Response(OrderSerializer(order).data)

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"payment_id": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={200: OrderSerializer()},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        reason = request.data.get("reason", "Admin cancellation")

        with transaction.atomic():
            try:
                order.cancel_order(reason)
                return Response(OrderSerializer(order).data)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminTicketViewSet(viewsets.ViewSet):
    permission_classes = [AdminPermission]

    def list(self, request):
        tickets = Ticket.objects.all()
        return Response(TicketSerializer(tickets, many=True).data)

    def retrieve(self, request, pk=None):
        ticket = get_object_or_404(Ticket, pk=pk)
        return Response(TicketSerializer(ticket).data)
