from razexOne.settings import ACTIVE_PAYMENT_GATEWAY
from booking.pg import BasePaymentGateway, PAYMENT_GATEWAYS

pg_class = PAYMENT_GATEWAYS[ACTIVE_PAYMENT_GATEWAY]


class PaymentService:
    pg = None
    pg_name = None

    def __init__(self, pg_name=None):
        _pg_class = pg_class
        if pg_name and pg_name != ACTIVE_PAYMENT_GATEWAY:
            _pg_class = PAYMENT_GATEWAYS[pg_name]

        self.pg_name = pg_name if pg_name else ACTIVE_PAYMENT_GATEWAY
        self.pg = _pg_class.get_instance()

    def create_payment_order(self, user, amount, tag=None):
        return self.pg.create_order(user, amount, tag)

    def confirm_payment(self, client_payment_info, stored_payment_info):
        return self.pg.confirm_payment(client_payment_info, stored_payment_info)

    def refund_payment(self, order_id):
        return self.pg.refund_payment(order_id)

    def get_webhook_details(self, payload, signature):
        return self.pg.get_webhook_details(payload, signature)

    def get_payment_id_from_webhook(self, payload):
        return self.pg.get_payment_id_from_webhook(payload)

    def get_payout_id_from_webhook(self, payload):
        return self.pg.get_payout_id_from_webhook(payload)
