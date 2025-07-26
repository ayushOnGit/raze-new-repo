from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from base.models import User, Wallet
from base.serializers import UserDetailSerializer, UserUpdateSerializer, UserSerializer, WalletSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.auth import AuthManager
from rest_framework.parsers import FormParser, MultiPartParser


class UserViewSet(viewsets.GenericViewSet):
    """Viewset for User-related operations"""
    queryset = User.objects.all()
    parser_classes = (FormParser, MultiPartParser)
    
    def get_serializer_class(self):
        if self.action in ["me", "update_me"]:
            return UserDetailSerializer if self.request.method == "GET" else UserUpdateSerializer
        return UserDetailSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get the logged-in user's details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_me(self, request):
        """Update the logged-in user's name or birthdate"""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        method="get",
        responses={200: WalletSerializer()},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_wallet(self, request):
        """Get the logged-in user's wallet"""
        wallet = Wallet.get_wallet_for_user(request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    parser_classes = (FormParser, MultiPartParser)

    @action(detail=True, methods=["post"])
    def api_key(self, request, pk=None):
        user = self.get_object()
        auth_manager = AuthManager.get_instance()
        auth_backend = auth_manager.get_auth_backend_for_user(user)
        token = auth_backend.generate_jwt_token(user.uid)
        return Response({"token": token})
