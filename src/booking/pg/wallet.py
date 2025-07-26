from .base import (
    BasePaymentGateway,
    PayoutRequest,
    PayoutStatus,
    PayoutResponse,
    WebhookPayload,
    WebhookEvent,
    PaymentOrderStatus,
    PaymentOrder,
)
from base.models import Wallet, WalletTransaction
from django.core.exceptions import ValidationError


class WalletPaymentGateway(BasePaymentGateway):

    def setup(self):
        pass

    def create_order(self, user, amount, tag=None):
        wallet = Wallet.get_wallet_for_user(user)
        trans = wallet.debit(amount, f"Debit for cart #{tag}")
        return PaymentOrder(
            id=trans.transaction_id, amount=amount, status=PaymentOrderStatus.SUCCESS
        )

    def confirm_payment(
        self, client_payment_info: str, stored_payment_info: str
    ) -> bool:
        """
        Dummy implementation for wallet payment gateway, since payments are always successful.
        client_payment_info : Should be returning the payment_id from the order object which is the transaction id.
        stored_payment_info : Should be the transaction id.
        """
        return client_payment_info == stored_payment_info

    def refund_payment(self, order_id: str) -> bool:
        """
        Get the transaction object using order_id and credit the amount back to the wallet.
        """
        trans = WalletTransaction.objects.get(transaction_id=order_id)
        amount = trans.amount
        wallet = trans.wallet
        wallet.credit(amount, f"Refund for transaction #{order_id}")
