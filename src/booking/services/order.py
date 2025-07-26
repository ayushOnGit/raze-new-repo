from booking.models import (
    Cart,
    Order,
    Ticket,
    Product,
    PaymentMode,
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from .payment import PaymentService
from django.core.exceptions import ValidationError
from booking.pg import PaymentOrderStatus
from razexOne.settings import ACTIVE_PAYMENT_GATEWAY, WALLET_PAYMENT_GATEWAY


class OrderService:
    def __init__(self, user):
        self.user = user

    # Get payment gateway based on chosen payment mode.
    def get_payment_gateway_for_cart(self, cart):
        if cart.payment_mode == PaymentMode.WALLET:
            return WALLET_PAYMENT_GATEWAY
        elif cart.payment_mode == PaymentMode.ONLINE:
            return ACTIVE_PAYMENT_GATEWAY
        else:
            raise ValidationError("Unknown payment mode")

    def create_order(self, cart_id):
        with transaction.atomic():
            cart = Cart.lock_cart(cart_id, self.user)
            payment_service = PaymentService(self.get_payment_gateway_for_cart(cart))
            amount = cart.net_price
            payment_id = None
            payment_gateway = None
            can_confirm = False
            if amount >= 1:
                payment_order = payment_service.create_payment_order(
                    self.user, amount, cart_id
                )
                payment_id = payment_order.id
                payment_gateway = payment_service.pg_name
                can_confirm = payment_order.status == PaymentOrderStatus.SUCCESS
            order = Order.create_order(cart, payment_id, payment_gateway)
            if can_confirm:
                order.confirm_payment()
            return order

    def create_recharge_order(self, amount):
        payment_service = PaymentService()  # Use default payment gateway
        payment_order = payment_service.create_payment_order(self.user, amount)
        order = Order.create_wallet_recharge_order(
            self.user, amount, payment_order.id, payment_service.pg_name
        )
        if payment_order.status == PaymentOrderStatus.SUCCESS:
            order.confirm_payment()
        return order

    def cancel_order(self, order_id):
        with transaction.atomic():
            order = Order.lock_order(order_id, self.user)
            cancelled = order.cancel_order()
            if cancelled and order.has_payment():
                # Refund payment if it was actually cancelled with this call.
                # We are initiating refund even though successfull orders cannot be cancelled
                # so that in case the payment succeeds after cancellation, the payment is refunded automatically.
                payment_service = PaymentService(order.payment_gateway)
                payment_service.refund_payment(order.payment_id)
                return order

    def confirm_payment(self, order_id, payment_info):
        with transaction.atomic():
            order = Order.lock_order(order_id, self.user)
            if not order.payment_gateway or not order.has_payment():
                raise ValidationError("Order does not have a payment.")
            payment_service = PaymentService(order.payment_gateway)
            if not payment_service.confirm_payment(payment_info, order.payment_id):
                raise ValidationError("Payment confirmation failed.")
            self.mark_confirm_or_refund(order)
            return order

    def mark_confirm_or_refund(self, order):
        try:
            order.confirm_payment()
        except ValidationError as e:
            if not order.is_failed():
                payment_service = PaymentService(order.payment_gateway)
                payment_service.refund_payment(order.payment_id)
                order.cancel_order()
        return order


class CartService:
    def __init__(self, user):
        self.user = user

    def change_quantity(self, cart_id, quantity):
        with transaction.atomic():
            cart = Cart.lock_cart(cart_id, self.user)
            cart.change_quantity(quantity)
            return cart

    def change_payment_mode(self, cart_id, payment_mode):
        with transaction.atomic():
            cart = Cart.lock_cart(cart_id, self.user)
            cart.change_payment_mode(payment_mode)
            return cart

    def cancel_cart(self, cart_id):
        with transaction.atomic():
            cart = Cart.lock_cart(cart_id, self.user)
            cart.cancel_cart()
            return cart
