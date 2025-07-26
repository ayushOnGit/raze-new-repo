from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.core.cache import cache
from django.utils.timezone import now

from .product import Product
from .event import Event
from base.models import User
from .quota import Quota
from django.db.models import Q


class PromoUserType(models.TextChoices):
    PROMOTER = "PROMOTER", "Promoter"
    END_USER = "END_USER", "End User"
    ALL = "ALL", "All"


class Promotion(models.Model):
    promo_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    products = models.ManyToManyField(Product, blank=True)
    all_products = models.BooleanField(default=True)
    code = models.CharField(max_length=100, unique=True, null=True)
    is_listed = models.BooleanField(default=True, help_text="Can normal users see this promotion?")
    is_active = models.BooleanField(default=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    discount_fixed = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    min_quantity = models.IntegerField(default=1)
    max_quantity = models.IntegerField(null=True)
    quantity_step = models.IntegerField(default=1)
    promo_owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    priority = models.IntegerField(default=0)
    applicable_user_type = models.CharField(
        max_length=10, choices=PromoUserType.choices, default=PromoUserType.ALL
    )
    created_on = models.DateTimeField(auto_now_add=True)
    end_user_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True
    )

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.name} - {self.event.name}"

    def clean(self):
        if (
            self.end_user_discount_percentage is not None
            and not 0 <= self.end_user_discount_percentage <= 100
        ):
            raise ValidationError(
                "End user discount percentage must be between 0 and 100"
            )
        if self.discount_percentage is None and self.discount_fixed is None:
            raise ValidationError(
                "Either discount percentage or fixed discount must be set"
            )
        if self.discount_percentage is not None and self.discount_fixed is not None:
            raise ValidationError(
                "Discount percentage and fixed discount cannnot be set together."
            )
        if (
            self.discount_percentage is not None
            and not 0 <= self.discount_percentage <= 100
        ):
            raise ValidationError("Discount percentage must be between 0 and 100")
        if self.discount_fixed is not None and self.discount_fixed < 0:
            raise ValidationError("Fixed discount must be positive")
        if self.min_order_value is not None and self.min_order_value < 0:
            raise ValidationError("Minimum order value must be positive")
        if (
            self.max_order_value is not None
            and self.max_order_value < self.min_order_value
        ):
            raise ValidationError(
                "Maximum order value must be greater than or equal to minimum order value"
            )
        if self.max_discount is not None and self.max_discount < 0:
            raise ValidationError("Maximum discount must be positive")
        if self.min_quantity < 1:
            raise ValidationError("Minimum quantity must be at least 1")
        if self.max_quantity is not None and self.max_quantity < self.min_quantity:
            raise ValidationError(
                "Maximum quantity must be greater than or equal to minimum quantity"
            )
        if self.quantity_step < 1:
            raise ValidationError("Quantity step must be at least 1")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self._post_save()

    def _post_save(self):
        products = self.products.all()
        if not self.all_products and not products.exists():
            self.all_products = True
            self.save()
        if self.all_products and products.exists():
            self.all_products = False
            self.save()

    def calculate_new_price(self, original_price):
        new_price = original_price
        if self.discount_percentage is not None:
            new_price = original_price * (1 - self.discount_percentage / 100)
        new_price = max(original_price - self.discount_fixed, 0)
        # apply max discount
        if self.max_discount is not None:
            new_price = min(new_price, original_price - self.max_discount)
        return new_price

    def check_order_value(self, order_value):
        if self.min_order_value is not None and order_value < self.min_order_value:
            return False
        if self.max_order_value is not None and order_value > self.max_order_value:
            return False
        return True

    def check_quantity(self, quantity):
        if quantity < self.min_quantity:
            return False
        if self.max_quantity is not None and quantity > self.max_quantity:
            return False
        if (quantity - self.min_quantity) % self.quantity_step != 0:
            return False
        return True

    def can_apply_promotion(self, cart):
        if not self.is_active:
            return False
        if self.code and cart.discount_coupon == self.code:
            return True
        if not self.check_order_value(cart.quantity):
            return False
        if not self.check_quantity(cart.gross_price):
            return False
        if self.applicable_user_type != PromoUserType.ALL:
            if self.applicable_user_type == PromoUserType.PROMOTER:
                if not cart.is_promoter:
                    return False
            elif self.applicable_user_type == PromoUserType.END_USER:
                if cart.is_promoter:
                    return False
            else:
                raise ValidationError("Invalid promo user type")
        product = cart.product
        if not product:
            return False
        if product.event != self.event:
            return False
        if not self.all_products and product not in self.products.all():
            return False
        if self.quota and self.quota.get_remaining_slots() < cart.quantity:
            return False
        return True
    
    @classmethod
    def get_listing_qs(cls):
        return cls.objects.filter(is_listed=True, is_active=True)
    
    @classmethod
    def list_for_product(cls, product):
        if not product.event:
            return cls.objects.none()
        return cls.get_listing_qs().filter(
            Q(all_products=True) | Q(products=product), event=product.event
        ).prefetch_related("quota")

    @classmethod
    def get_active_promotions(cls, event, include_user_promos=True):
        if not include_user_promos:
            return cls.objects.filter(
                event=event, is_active=True, promo_owner__isnull=True
            )
        return cls.objects.filter(event=event, is_active=True)

    @classmethod
    def get_promotion_by_code(cls, code):
        return cls.objects.filter(code=code).first()

    @classmethod
    def apply_promotions(cls, cart):
        new_price = cart.gross_price
        coupon_promo = None
        promo_ids = []
        end_user_discount_percentage = None
        if cart.discount_coupon:
            coupon_promo = (
                cls.objects.filter(code=cart.discount_coupon)
                .prefetch_related("quota")
                .first()
            )
            if not coupon_promo:
                raise ValidationError("Invalid coupon code")
            if not coupon_promo.can_apply_promotion(cart):
                raise ValidationError("Coupon code cannot be applied to this cart")
        # apply system promotions
        promotions = (
            cls.get_active_promotions(cart.product.event)
            .filter(code__isnull=True)
            .order_by("priority")
            .prefetch_related("quota")
        )
        # Add promo coupon to the end of the list
        if coupon_promo:
            promotions = list(promotions)
            promotions.append(coupon_promo)
        for promo in promotions:
            if promo.can_apply_promotion(cart):
                new_price = promo.calculate_new_price(new_price)
                promo_ids.append(promo.promo_id)
                if promo.end_user_discount_percentage is not None:
                    end_user_discount_percentage = (
                        promo.end_user_discount_percentage
                        if end_user_discount_percentage is None
                        else max(
                            end_user_discount_percentage,
                            promo.end_user_discount_percentage,
                        )
                    )
        return (new_price, promo_ids, end_user_discount_percentage)
