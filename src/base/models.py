from datetime import timedelta
from django.db import models

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from razexOne.settings import (
    ACTIVE_AUTH_BACKENDS,
    OTP_EXPIRY_AFTER_MINUTES,
    OTP_SEND_INTERVAL_SECONDS,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.validators import MinValueValidator
from razexOne.storages import PublicMediaStorage
from django.utils.timezone import now
import random
from .helpers.phone_number import validate_phone_number


class UserManager(BaseUserManager):
    def create_user(self, uid: str, auth_backend: str, **extra_fields) -> "User":
        if not uid:
            raise ValueError("The uid must be set")
        if auth_backend not in ACTIVE_AUTH_BACKENDS:
            raise ValueError("Invalid auth backend")

        user = self.create(uid=uid, auth_backend=auth_backend, **extra_fields)
        user.save()
        # Create wallet for the user
        _ = Wallet.get_wallet_for_user(user)
        return user

    def create_superuser(self, user_id, uid, auth_backend, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(uid=uid, auth_backend=auth_backend, **extra_fields)

    def get_or_create(self, uid: str, auth_backend: str, **extra_fields) -> "User":
        try:
            return self.get(uid=uid, auth_backend=auth_backend)
        except self.model.DoesNotExist:
            return self.create_user(uid=uid, auth_backend=auth_backend, **extra_fields)

    def get_user(self, uid: str, auth_backend: str) -> "User":
        return self.get(uid=uid, auth_backend=auth_backend)


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    uid = models.CharField(max_length=255)
    auth_backend = models.CharField(max_length=128, default="native")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date joined")
    is_active = models.BooleanField(default=True, verbose_name="Is active")
    is_staff = models.BooleanField(default=False, verbose_name="Is site admin")
    phone_number = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Phone number",
        validators=[validate_phone_number],
        help_text="Phone number must be in E.164 format (e.g., +911234567890).",
    )
    email = models.EmailField(
        max_length=255, blank=True, null=True, verbose_name="Email"
    )
    is_email_verified = models.BooleanField(
        default=False, verbose_name="Is email verified"
    )
    birthdate = models.DateField(blank=True, null=True, verbose_name="Birthdate")
    is_onboarded = models.BooleanField(default=False, verbose_name="Is onboarded")
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        storage=PublicMediaStorage,
        blank=True,
        null=True,
        verbose_name="Profile picture",
    )
    password = models.CharField(max_length=128, blank=True, null=True)  # For admin login
    allow_app_notification = models.BooleanField(
        default=True, verbose_name="Allow app notifications"
    )

    USERNAME_FIELD = "user_id"
    REQUIRED_FIELDS = ["uid", "auth_backend"]

    objects = UserManager()

    def __str__(self):
        return self.name or self.phone_number or self.email

    def clean(self, *args, **kwargs):
        # If name, phone_number and email are set, mark user as onboarded
        if self.name and self.phone_number and self.email and self.birthdate:
            self.is_onboarded = True

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = (
            "phone_number",
            "email",
        )
        unique_together = (("auth_backend", "uid"),)


class Wallet(models.Model):
    wallet_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    can_receive_payments = models.BooleanField(default=False)

    def __str__(self):
        return f"Wallet {self.wallet_id} - {self.user.name}"

    def credit(self, amount, description=None, is_locked=False):
        """
        Credit the wallet with the given amount and return the transaction.
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        with transaction.atomic():
            # lock the wallet
            if not is_locked:
                self = Wallet.lock_wallet(self.wallet_id)
            self.balance += amount
            self.save()
            return WalletTransaction.objects.create(
                wallet=self,
                amount=amount,
                transaction_type="credit",
                description=description,
            )

    def debit(self, amount, description=None, is_locked=False):
        """
        Debit the wallet with the given amount and return the transaction.
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        with transaction.atomic():
            # lock the wallet
            if not is_locked:
                self = Wallet.lock_wallet(self.wallet_id)
            if self.balance < amount:
                raise ValidationError("Insufficient balance")
            self.balance -= amount
            self.save()
            return WalletTransaction.objects.create(
                wallet=self,
                amount=amount,
                transaction_type="debit",
                description=description,
            )

    def get_transactions(self):
        return WalletTransaction.objects.filter(wallet=self).order_by("-timestamp")

    @classmethod
    def get_wallet_for_user(cls, user):
        """
        Get or create wallet for the given user.
        """
        wallet, _ = cls.objects.get_or_create(user=user)
        return wallet

    @classmethod
    def lock_wallet(cls, wallet_id):
        return cls.objects.select_for_update().get(pk=wallet_id)

    @classmethod
    def transfer(cls, from_wallet_id, to_wallet_id, amount, description=None):
        """
        Transfer money from one wallet to another.
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        with transaction.atomic():
            from_wallet = cls.lock_wallet(from_wallet_id)
            to_wallet = cls.lock_wallet(to_wallet_id)
            if not to_wallet.can_receive_payments:
                raise ValidationError("Cannot transfer to this wallet")
            from_trans = from_wallet.debit(amount, description, is_locked=True)
            to_trans = to_wallet.credit(amount, description, is_locked=True)
            return (from_trans, to_trans)


class WalletTransaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ("credit", "Credit"),
            ("debit", "Debit"),
        ],
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.wallet.user.name}"


import random


class OTP(models.Model):
    phone_number = models.CharField(
        max_length=15,
        validators=[validate_phone_number],
        help_text="Phone number must be in E.164 format (e.g., +911234567890).",
        unique=True,
        verbose_name="Phone number",
    )  # Store in E.164 format (+1234567890)
    otp = models.CharField(max_length=6)  # 6-digit OTP
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # OTP expiration time
    last_sent_at = models.DateTimeField(null=True, default=None)  # Last sent time

    def __str__(self):
        return f"OTP for {self.phone_number} - {self.otp}"

    def is_valid(self):
        """Check if the OTP is still valid."""
        return now() < self.expires_at

    def mark_sent(self):
        """Mark the OTP as sent."""
        self.last_sent_at = now()
        self.save()

    def can_send(self):
        """Check if the OTP can be sent again."""
        if self.last_sent_at is None:
            return True
        return (now() - self.last_sent_at).total_seconds() > OTP_SEND_INTERVAL_SECONDS

    @classmethod
    def get_otp(cls, phone_number):
        """Get the OTP for the given phone number."""
        try:
            otp = cls.objects.get(phone_number=phone_number)
            return otp
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_or_create_otp(cls, phone_number):
        """Create a new OTP for the given phone number."""
        validate_phone_number(phone_number)  # Will throw if invalid
        # Try to get existing OTP
        existing_otp = cls.get_otp(phone_number)
        if existing_otp:
            # Return if OTP is still valid
            if existing_otp.is_valid():
                return existing_otp
            # If OTP is expired, delete it
            existing_otp.delete()
        # If no valid OTP exists, create a new one
        otp = cls.generate_otp()
        expires_at = now() + timedelta(minutes=OTP_EXPIRY_AFTER_MINUTES)
        new_otp = cls.objects.create(
            phone_number=phone_number,
            otp=otp,
            expires_at=expires_at,
        )
        return new_otp

    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP."""
        return str(random.randint(100000, 999999))
