import time
from typing import Tuple
from firebase_admin import auth
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from razexOne.settings import ACTIVE_AUTH_BACKENDS
from .models import User
from .helpers.jwt import decode_jwt, encode_jwt


class DjangoProxyBackend(object):
    def authenticate(self, **kwargs):
        # Disabling default django authentication
        return None


class RazexBaseAuthentication(BaseAuthentication):
    key = None

    def verify_key(self, key):
        if not self.key:
            raise ValueError("Key is not set")
        if key not in ACTIVE_AUTH_BACKENDS:
            return False
        return key == self.key

    def get_user(self, uid: str) -> User:
        try:
            user = User.objects.get_user(uid=uid, auth_backend=self.key)
            return user
        except User.DoesNotExist:
            return None

    def generate_jwt_token(self, uid: str) -> str:
        raise NotImplementedError("JWT Tokens are not supported for this auth type.")


class FirebaseAuthentication(RazexBaseAuthentication):
    def __init__(self):
        super().__init__()
        self.key = "firebase"

    def authenticate(self, request):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None  # No authentication credentials provided

        id_token = auth_header.split("Bearer ")[-1]

        try:
            # Verify Firebase token
            decoded_token = auth.verify_id_token(id_token)
            firebase_uid = decoded_token["uid"]

            # Try to get user from database
            try:
                user = User.objects.get_user(uid=firebase_uid, auth_backend=self.key)
            except User.DoesNotExist:
                # get user info from firebase
                user_info = auth.get_user(firebase_uid)
                email = user_info.email
                name = user_info.display_name
                phone_number = user_info.phone_number
                # if not name:
                #     if email:
                #         name = email.split("@")[0]
                #     elif phone_number:
                #         name = phone_number
                #     else:
                #         name = firebase_uid
                # Create user if not exists
                user = User.objects.create_user(
                    uid=firebase_uid,
                    auth_backend=self.key,
                    email=email,
                    name=name,
                    phone_number=phone_number,
                )

            return (user, None)  # DRF requires (user, auth) tuple
        except Exception as exc:
            raise AuthenticationFailed("Invalid Firebase token") from exc


class NativeAuthentication(RazexBaseAuthentication):
    def __init__(self):
        super().__init__()
        self.key = "native"

    REQUIRED_FIELDS = ["uid", "auth_backend", "expiry"]
    EXPIRY_DURATION = 30 * 24 * 60 * 60  # 30 days

    def has_expired(self, expiry: int) -> bool:
        return expiry < time.time()

    def get_uid_from_jwt_token(self, token: str) -> Tuple[str, str]:
        try:
            data = decode_jwt(token)
            # If auth_backend field is not present, return None
            if "auth_backend" not in data:
                return None
            auth_backend = data["auth_backend"]
            if auth_backend != self.key:
                return None
            for field in self.REQUIRED_FIELDS:
                if field not in data:
                    raise AuthenticationFailed(f"Missing field: {field}")
            try:
                expiry = int(data["expiry"])
            except ValueError as exc:
                raise AuthenticationFailed("Invalid expiry") from exc
            if self.has_expired(expiry):
                raise AuthenticationFailed("Token has expired")
            return data["uid"]
        except Exception as exc:
            raise AuthenticationFailed("Invalid JWT Token") from exc

    def generate_jwt_token(self, uid: str) -> str:
        expiry = int(time.time()) + self.EXPIRY_DURATION
        payload = {"uid": uid, "auth_backend": self.key, "expiry": expiry}
        return encode_jwt(payload)

    def create_user(self, uid: str, **kwargs: dict) -> "User":
        return User.objects.create_user(uid=uid, auth_backend=self.key, **kwargs)

    def authenticate(self, request):
        # Extract token from jwt header
        auth_header = request.headers.get("Jwt")
        if not auth_header:
            return None
        # Extract uid from jwt token
        uid = self.get_uid_from_jwt_token(auth_header)
        if not uid:
            return None
        # Try to get user from database
        user = User.objects.get_user(uid=uid, auth_backend=self.key)
        return (user, None)


class OTPAuthentication(RazexBaseAuthentication):
    def __init__(self):
        super().__init__()
        self.key = "otp"

    REQUIRED_FIELDS = ["phone", "expiry", "auth_backend"]
    EXPIRY_DURATION = 30 * 24 * 60 * 60  # 30 days

    def generate_jwt_token(self, uid: str) -> str:
        # Generate JWT token with phone number and expiry
        expiry = int(time.time()) + self.EXPIRY_DURATION
        payload = {"phone": uid, "expiry": expiry, "auth_backend": self.key}
        return encode_jwt(payload)

    def has_expired(self, expiry: int) -> bool:
        return expiry < time.time()

    def get_phone_from_jwt_token(self, token: str) -> str:
        try:
            data = decode_jwt(token)
        except Exception as exc:
            raise AuthenticationFailed("Invalid JWT Token") from exc
        # Check for auth_backend field
        if "auth_backend" not in data:
            return None
        auth_backend = data["auth_backend"]
        if auth_backend != self.key:
            return None
        # Now we are sure this jwt token is for this backend
        # Check for required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                raise AuthenticationFailed(f"Missing field: {field}")
        try:
            expiry = int(data["expiry"])
        except ValueError as exc:
            raise AuthenticationFailed("Invalid expiry") from exc
        if self.has_expired(expiry):
            raise AuthenticationFailed("Token has expired")
        return data["phone"]

    def authenticate(self, request):
        # Extract token from jwt header
        auth_header = request.headers.get("Jwt")
        if not auth_header:
            return None
        # Extract phone number from jwt token
        phone_number = self.get_phone_from_jwt_token(auth_header)
        if not phone_number:
            return None
        # Try to get user from database
        user = self.get_user(phone_number)
        if user:
            return (user, None)
        # If user not found, create a new user
        user = User.objects.create_user(
            uid=phone_number, auth_backend=self.key, phone_number=phone_number
        )
        return (user, None)


class AuthManager:

    AUTH_BACKEND_CLASSES = [
        FirebaseAuthentication,
        NativeAuthentication,
        OTPAuthentication,
    ]

    def __init__(self):
        self.backends = {}
        for backend_class in self.AUTH_BACKEND_CLASSES:
            backend_instance = backend_class()
            self.backends[backend_instance.key] = backend_instance

    def get_auth_backend(self, key: str) -> RazexBaseAuthentication:
        if key not in self.backends:
            raise ValueError(f"Invalid auth backend: {key}")
        if key not in ACTIVE_AUTH_BACKENDS:
            raise ValueError(f"Auth backend {key} is not active")
        return self.backends.get(key)

    def get_auth_backend_for_user(self, user: User) -> RazexBaseAuthentication:
        if not user.auth_backend:
            raise ValueError("User does not have an auth backend")
        return self.get_auth_backend(user.auth_backend)

    @classmethod
    def get_instance(cls):
        """
        Singleton pattern to get the AuthManager instance.
        """
        if not hasattr(cls, "instance"):
            cls.instance = cls()
        return cls.instance
