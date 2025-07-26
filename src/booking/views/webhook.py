from rest_framework import viewsets, serializers, filters
from booking.services.payment import PaymentService
from booking.models import Order
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from booking.services.webhook import WebhookService


class WebhookViewSet(viewsets.ViewSet):
    # Razorpay Webhook for Payment Confirmation
    @api_view(["POST"])
    @permission_classes([AllowAny])
    @csrf_exempt
    def razorpay(request):
        PAZORPAY_PG_NAME = "RazorpayPaymentGateway"
        try:
            payload = request.body
            signature = request.headers.get("X-Razorpay-Signature")

            webhook_service = WebhookService()
            webhook_service.process_pg_webhook(PAZORPAY_PG_NAME, payload, signature)

            return Response({"status": "success"})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
