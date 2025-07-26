from django.db import models, transaction
from django.core.exceptions import ValidationError
from base.models import Wallet, WalletTransaction
from django.core.validators import MinValueValidator


class WalletPayout(models.Model):
    payout_id = models.AutoField(primary_key=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    reference_id = models.CharField(max_length=255, blank=True, null=True)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    debit_transaction = models.ForeignKey(
        WalletTransaction, on_delete=models.SET_NULL, null=True
    )
    payment_link = models.URLField(blank=True, null=True)

    def clean(self):
        # Remove payment_link if the payout is in a final state.
        if self.status != "pending":
            self.payment_link = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payout {self.payout_id} - {self.wallet.user.name}"

    def complete_payout(self):
        """
        Complete the payout and update the status.
        """
        if self.status == "failed":
            raise ValidationError("Cannot complete a failed payout")
        self.status = "completed"
        self.save()
        return self

    def fail_payout(self):
        """
        Fail the payout and credit back the amount to the wallet.
        """
        if self.status == "failed":
            return self
        with transaction.atomic():
            self.status = "failed"
            self.save()
            self.wallet.credit(self.amount, f"Failed payout {self.payout_id}")
            return self

    @classmethod
    def create_payout(
        cls,
        wallet,
        amount,
        reference_id,
        payment_gateway,
        payment_link=None,
        description=None,
        is_locked=False,
    ):
        """
        Create a payout for the given wallet and debit the amount from the wallet.
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        with transaction.atomic():
            trans = wallet.debit(amount, description, is_locked)
            return cls.objects.create(
                wallet=wallet,
                amount=amount,
                status="pending",
                description=description,
                debit_transaction=trans,
                reference_id=reference_id,
                payment_gateway=payment_gateway,
                payment_link=payment_link,
            )

    @classmethod
    def wallet_payout_qs(cls, wallet):
        return cls.objects.filter(wallet=wallet).order_by("-timestamp")

    @classmethod
    def get_payout_by_reference_id(cls, reference_id, payment_gateway=None):
        return cls.objects.get(
            reference_id=reference_id, payment_gateway=payment_gateway
        )

    @classmethod
    def lock_payout_by_reference_id(cls, reference_id, payment_gateway=None):
        return cls.objects.select_for_update().get(
            reference_id=reference_id, payment_gateway=payment_gateway
        )

    @classmethod
    def complete_payout_by_reference_id(cls, reference_id, payment_gateway=None):
        """
        Complete the payout with the given id.
        """
        with transaction.atomic():
            payout = cls.lock_payout_by_reference_id(reference_id, payment_gateway)
            return payout.complete_payout()

    @classmethod
    def fail_payout_by_reference_id(cls, reference_id, payment_gateway=None):
        """
        Fail the payout with the given id.
        """
        with transaction.atomic():
            payout = cls.lock_payout_by_reference_id(reference_id, payment_gateway)
            return payout.fail_payout()

    @classmethod
    def pending_payouts_qs(cls):
        return cls.objects.filter(status="pending")
