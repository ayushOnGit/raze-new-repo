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
import razorpay
from razexOne.settings import (
    RAZORPAY_API_KEY,
    RAZORPAY_API_SECRET,
    RAZORPAY_WEBHOOK_SECRET,
    RAZORPAY_ACCOUNT_NUMBER,
    PAYOUT_EXPIRY_IN_SECS,
)
import json
import requests
import time


class RazorpayPaymentGateway(BasePaymentGateway):
    client = None

    def setup(self):
        client = razorpay.Client(auth=(RAZORPAY_API_KEY, RAZORPAY_API_SECRET))
        client.set_app_details({"title": "RazexOne", "version": "1.0"})
        self.client = client

    def create_order(self, user, amount, tag=None):
        # Amount in paise
        # Convert amount from Decimal to int
        amount = int(amount * 100)
        order = self.client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "payment_capture": 1,
            }
        )
        return PaymentOrder(
            id=order["id"], amount=amount, status=PaymentOrderStatus.PENDING
        )

    def confirm_payment(
        self, client_payment_info: str, stored_payment_info: str
    ) -> bool:
        """
        client_payment_info : JSON string containing payment information from client
        stored_payment_info : Razorpay order id stored in the database

        Returns True if payment is successful, False otherwise
        """
        razorpay_order_id = stored_payment_info
        payment_info = json.loads(client_payment_info)
        """
        Format expected in client_payment_info:
        {
            "razorpay_payment_id": "pay_1Iv3c3K1hjB2Gv",
            "razorpay_order_id": "order_1Iv3c3K1hjB2Gv",
            "razorpay_signature": "f5d8a5b9a7d6f5b7f6d5a7"
        }
        """
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": payment_info["razorpay_payment_id"],
                    "razorpay_signature": payment_info["razorpay_signature"],
                }
            )
            # self.client.payment.capture(payment_info['razorpay_payment_id'], payment_info['amount'])
            return True
        except Exception as e:
            print(f"Failed to confirm payment: {e}")
            return False

    def refund_payment(self, order_id: str) -> bool:
        try:
            self.client.payment.refund(order_id)
            return True
        except Exception as e:
            print(f"Failed to refund payment: {e}")

    def get_payment_id_from_webhook(self, payload: WebhookPayload) -> str:
        if (
            payload.event == WebhookEvent.PAYMENT_SUCCESS
            or payload.event == WebhookEvent.PAYMENT_FAILED
        ):
            return payload.data["payment_id"]
        else:
            raise ValueError("Invalid event type")

    def get_payout_id_from_webhook(self, payload: WebhookPayload) -> str:
        if (
            payload.event == WebhookEvent.PAYOUT_SUCCESS
            or payload.event == WebhookEvent.PAYOUT_FAILED
        ):
            return payload.data["payout_id"]
        else:
            raise ValueError("Invalid event type")

    def get_webhook_details(self, payload, signature) -> str:
        self.client.utility.verify_webhook_signature(
            payload, signature, RAZORPAY_WEBHOOK_SECRET
        )

        payload_data = json.loads(payload)
        event = payload_data.get("event")

        webhook_event = WebhookEvent.NO_OP
        data = {}

        if event == "payment.captured":
            webhook_event = WebhookEvent.PAYMENT_SUCCESS
            data["payment_id"] = payload_data["payload"]["payment"]["entity"]["id"]
            data["amount"] = payload_data["payload"]["payment"]["entity"]["amount"]
        elif event == "payment.failed":
            webhook_event = WebhookEvent.PAYMENT_FAILED
            data["payment_id"] = payload_data["payload"]["payment"]["entity"]["id"]
            data["amount"] = payload_data["payload"]["payment"]["entity"]["amount"]
        elif event == "payout.failed" or event == "payout.rejected":
            webhook_event = WebhookEvent.PAYOUT_FAILED
            data["payout_id"] = payload_data["payload"]["payout"]["entity"]["id"]
            data["amount"] = payload_data["payload"]["payout"]["entity"]["amount"]
        elif event == "payout.processed":
            webhook_event = WebhookEvent.PAYOUT_SUCCESS
            data["payout_id"] = payload_data["payload"]["payout"]["entity"]["id"]
            data["amount"] = payload_data["payload"]["payout"]["entity"]["amount"]

        return WebhookPayload(event=webhook_event, data=data)

    def create_payout(self, payout_request: PayoutRequest) -> PayoutResponse:
        """
        Payout is part of RazorpayX platform which is not supported by the python sdk.
        We need to manually make a request to the RazorpayX API.

        https://razorpay.com/docs/api/x/payout-links/create/use-contact-details

        Sample Curl Request:

        curl -u <YOUR_KEY>:<YOUR_SECRET> \
        -X POST https://api.razorpay.com/v1/payout-links \
        -H "Content-Type: application/json" \
        -d '{
            "account_number": "7878780080857996",
            "contact": {
                "name": "Gaurav Kumar",
                "contact": "912345678",
                "email": "gaurav.kumar@example.com",
                "type": "customer"
            }, // Only applicable when you have the contact details of the recipient. 
            "amount": 1000,
            "currency": "INR",
            "purpose": "refund",
            "description": "Payout link for Gaurav Kumar",
            "receipt": "Receipt No. 1",
            "send_sms": true,
            "send_email": true,
            "notes": {
                "notes_key_1":"Tea, Earl Grey, Hot",
                "notes_key_2":"Tea, Earl Grey… decaf."
            },
            "expire_by": 1545384058 // This parameter can be used only if you have enabled the expiry feature for Payout Links.
        }'


        Sample Response:

        {
            "id": "poutlk_00000000000001",
            "entity": "payout_link",
            "contact": {
                "name": "Gaurav Kumar",
                "email": "gaurav.kumar@example.com",
                "contact": "912345678"
            },
            
            "purpose": "refund",
            "status": "issued",
            "amount": 1000,
            "currency": "INR",
            "description": "Payout link for Gaurav Kumar",
            "short_url": "https://rzp.io/i/3b1Tw6",
            "created_at": 1545383037,
            "contact_id": "cont_00000000000001",
            "send_sms": true,
            "send_email": true,
            "fund_account_id": null,
            "cancelled_at": null,
            "attempt_count": 0,
            "receipt": "Receipt No. 1",
            "notes": {
                "notes_key_1":"Tea, Earl Grey, Hot",
                "notes_key_2":"Tea, Earl Grey… decaf."
            },
            "expire_by": 1545384058,
            "expired_at": 1545384658
        }
        """

        url = "https://api.razorpay.com/v1/payout-links"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "account_number": RAZORPAY_ACCOUNT_NUMBER,
            "contact": {
                "name": payout_request.name,
                "contact": payout_request.phone_number,
                "type": "customer",
            },
            "amount": int(payout_request.amount * 100),
            "currency": "INR",
            "purpose": "refund",
            "description": payout_request.description,
            "receipt": "Payout Receipt",
            "send_sms": True,
            "send_email": False,
        }

        if PAYOUT_EXPIRY_IN_SECS != None:
            data["expire_by"] = int(time.time()) + PAYOUT_EXPIRY_IN_SECS

        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(data),
            auth=(RAZORPAY_API_KEY, RAZORPAY_API_SECRET),
        )
        response_data = response.json()

        return PayoutResponse(
            id=response_data["id"],
            status=PayoutStatus.PENDING,
            amount=response_data["amount"] / 100,
            payment_link=response_data["short_url"],
        )
