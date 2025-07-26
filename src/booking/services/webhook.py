from django.db import transaction
from booking.services.payment import PaymentService
from booking.models import Order
from booking.services.order import OrderService
from booking.models import WalletPayout
from booking.pg import WebhookEvent


class WebhookService:

    def process_pg_webhook(self, pg_name, payload, signature):
        payment_service = PaymentService(pg_name)
        webhook_details = payment_service.get_webhook_details(payload, signature)

        if webhook_details.event == WebhookEvent.PAYMENT_SUCCESS:
            payment_id = payment_service.get_payment_id_from_webhook(webhook_details)

            with transaction.atomic():
                order = Order.objects.select_for_update().get(
                    payment_id=payment_id, payment_gateway=pg_name
                )
                order_service = OrderService(order.user)
                order_service.mark_confirm_or_refund(order)

        elif webhook_details.event == WebhookEvent.PAYMENT_FAILED:
            payment_id = payment_service.get_payment_id_from_webhook(webhook_details)

            with transaction.atomic():
                order = Order.objects.select_for_update().get(
                    payment_id=payment_id, payment_gateway=pg_name
                )
                order.cancel_order("Payment Failed")

        elif webhook_details.event == WebhookEvent.PAYOUT_SUCCESS:
            payout_id = payment_service.get_payout_id_from_webhook(webhook_details)
            WalletPayout.complete_payout_by_reference_id(payout_id, pg_name)

        elif webhook_details.event == WebhookEvent.PAYOUT_FAILED:
            payout_id = payment_service.get_payout_id_from_webhook(webhook_details)
            WalletPayout.fail_payout_by_reference_id(payout_id, pg_name)

        else:
            raise ValueError("Invalid webhook event")
