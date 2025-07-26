from django.urls import path, include
from rest_framework import routers
from base.views import (
    UserViewSet,
    UserAdminViewSet,
    RootView,
    HealthCheckView,
    WalletTransactionViewSet,
    WalletAdminViewSet,
    OTPViewSet,
    AdminOTPViewSet,
)


router = routers.DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"admin/users", UserAdminViewSet, basename="user-admin")

router.register(
    r"wallet/transaction", WalletTransactionViewSet, basename="wallet-transaction"
)
router.register(r"admin/wallets", WalletAdminViewSet, basename="wallet-admin")

router.register(r"otp", OTPViewSet, basename="otp")
router.register(r"admin/otp", AdminOTPViewSet, basename="otp-admin")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", RootView.as_view(), name="root"),
    path("healthz/", HealthCheckView.as_view(), name="health-check"),
] + router.urls
