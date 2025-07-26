from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.core.cache import cache
from django.utils.timezone import now
from django.core.validators import MinValueValidator

from .event import Event, VenueLayoutSection, Subevent
from .quota import Quota


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    description = models.TextField(blank=True, null=True)
    sale_start = models.DateTimeField(null=True)
    sale_end = models.DateTimeField(null=True)
    section = models.ForeignKey(
        VenueLayoutSection, null=True, blank=True, on_delete=models.SET_NULL
    )
    subevent = models.ForeignKey(
        Subevent, null=True, blank=True, on_delete=models.SET_NULL
    )
    is_active = models.BooleanField(default=True)
    tickets_active_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.event.name}"

    def is_ticket_active(self):
        return self.tickets_active_until is None or now() <= self.tickets_active_until

    def is_sale_active(self):
        if not self.is_active:
            return False

        self_sale_active = True
        if self.sale_start is not None and self.sale_end is not None:
            self_sale_active = self.sale_start <= now() <= self.sale_end
        elif self.sale_start is not None:
            self_sale_active = self.sale_start <= now()
        elif self.sale_end is not None:
            self_sale_active = now() <= self.sale_end
        if not self_sale_active:
            return False
        if not self.event.is_sale_active():
            return False
        return True

    @cached_property
    def quota_ids(self):
        cache_key = f"product_{self.product_id}_quota_ids"
        quota_ids = cache.get(cache_key)
        if quota_ids is None:
            quota_ids = Quota.get_quota_ids_for_product(self.product_id)
            cache.set(cache_key, quota_ids, timeout=5 * 60)
        return quota_ids
