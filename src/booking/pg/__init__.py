from .razorpay import RazorpayPaymentGateway
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
from .wallet import WalletPaymentGateway

PAYMENT_GATEWAYS = {
    "razorpay": RazorpayPaymentGateway,
    "wallet": WalletPaymentGateway,
}

AVAILABLE_PAYMENT_GATEWAYS = list(PAYMENT_GATEWAYS.keys())
