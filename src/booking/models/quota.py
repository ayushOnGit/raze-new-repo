from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class Quota(models.Model):
    quota_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    max_count = models.IntegerField(validators=[MinValueValidator(1)])
    slots_booked = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )  # Track booked slots directly
    products = models.ManyToManyField("Product", related_name="quotas", blank=True)
    promo = models.OneToOneField(
        "Promotion",
        on_delete=models.CASCADE,
        related_name="quota",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    def clean(self):
        if self.slots_booked > self.max_count:
            raise ValidationError("Slots booked cannot exceed max count")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def is_full(self):
        return self.slots_booked >= self.max_count

    def get_remaining_slots(self):
        return self.max_count - self.slots_booked

    @classmethod
    def get_quota_ids_for_product(cls, product_id):
        return cls.objects.filter(products__product_id=product_id).values_list(
            "quota_id", flat=True
        )

    @classmethod
    def get_quota_id_for_promotion(cls, promo_id):
        return cls.objects.filter(promo__promo_id=promo_id).values_list(
            "quota_id", flat=True
        )

    @classmethod
    def get_quota_for_product(cls, product_id):
        return cls.objects.filter(products__product_id=product_id).first()

    @classmethod
    def get_quota_for_promotion(cls, promo_id):
        return cls.objects.filter(promo__promo_id=promo_id).first()
