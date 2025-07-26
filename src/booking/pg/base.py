from dataclasses import dataclass
from typing import Optional
from enum import Enum


@dataclass
class PayoutRequest:
    amount: int
    user_id: int
    name: str
    phone_number: str
    description: str


class PayoutStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PayoutResponse:
    id: str
    status: PayoutStatus
    amount: int
    payment_link: Optional[str] = None


class WebhookEvent(Enum):
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    PAYOUT_SUCCESS = "payout_success"
    PAYOUT_FAILED = "payout_failed"
    NO_OP = "no_op"


@dataclass
class WebhookPayload:
    event: WebhookEvent
    data: dict

class PaymentOrderStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class PaymentOrder:
    id: str
    amount: int
    status: PaymentOrderStatus

class BasePaymentGateway:

    def __init__(self):
        pass

    def setup(self):
        raise NotImplementedError

    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
            cls._instance.setup()
        return cls._instance

    def create_order(self, user, amount, tag=None) -> PaymentOrder:
        raise NotImplementedError

    def confirm_payment(
        self, client_payment_info: str, stored_payment_info: str
    ) -> bool:
        raise NotImplementedError

    def refund_payment(self, order_id: str) -> bool:
        raise NotImplementedError

    def get_payment_id_from_webhook(self, payload: WebhookPayload) -> str:
        raise NotImplementedError

    def get_payout_id_from_webhook(self, payload: WebhookPayload) -> str:
        raise NotImplementedError

    def get_webhook_details(self, payload, signature) -> WebhookPayload:
        raise NotImplementedError

    def create_payout(self, payout_request: PayoutRequest) -> PayoutResponse:
        raise NotImplementedError
