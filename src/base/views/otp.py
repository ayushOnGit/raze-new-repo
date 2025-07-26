from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from base.models import OTP
from base.serializers import (
    OTPSerializer,
)
from base.helpers.api_permissions import AdminPermission, LoggedIn
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from razexOne.settings import OTP_EXPIRY_AFTER_MINUTES, DEBUG
from razexOne.sns import SNSService
from base.auth import OTPAuthentication
from base.helpers.phone_number import validate_phone_number


class AdminOTPViewSet(viewsets.ModelViewSet):
    """
    Admin Viewset for OTP.
    admin users can list OTP for all users and can filter by phone number.
    """

    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    serializer_class = OTPSerializer
    queryset = OTP.objects.all()
    filterset_fields = ["phone_number"]
    http_method_names = ["get", "patch", "delete"]

    ordering_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]


class OTPViewSet(viewsets.GenericViewSet):
    """
    Viewset for OTP for sending and verifying OTP.
    """

    permission_classes = [AllowAny]
    serializer_class = OTPSerializer

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "otp": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="OTP code, only in debug mode",
                    ),
                },
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def send_otp(self, request):
        """
        Send OTP to the user's phone number.
        """
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return Response(
                {"error": "Phone number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = OTP.get_or_create_otp(phone_number)

        if not otp.can_send():
            return Response(
                {"error": "OTP already sent. Please wait for a while."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sns = SNSService.get_instance()
        try:
            sns.send_otp(phone_number, otp.otp, OTP_EXPIRY_AFTER_MINUTES)
            otp.mark_sent()
        except sns.client.exceptions.InvalidParameterValue as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        resp = {"message": "OTP sent successfully"}
        if DEBUG:
            resp["otp"] = otp.otp
        return Response(resp, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        operation_summary="Verify OTP",
        operation_description="Verify OTP for the user's phone number and return JWT token. Pass this token in the header for all subsequent requests.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone_number", "otp"],
            properties={
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                "otp": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "Jwt": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def verify_otp(self, request):
        """
        Verify OTP for the user's phone number.
        """
        phone_number = request.data.get("phone_number")
        otp_code = request.data.get("otp")

        if not phone_number or not otp_code:
            return Response(
                {"error": "Phone number and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate phone number
        try:
            validate_phone_number(phone_number)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp = OTP.objects.get(phone_number=phone_number, otp=otp_code)
            if not otp.is_valid():
                return Response(
                    {"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST
                )
            # delete the otp instance so that it can't be used again
            otp.delete()
            # Generate JWT token for this phone number
            jwt_token = OTPAuthentication().generate_jwt_token(phone_number)
            return Response({"Jwt": jwt_token}, status=status.HTTP_200_OK)
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )
