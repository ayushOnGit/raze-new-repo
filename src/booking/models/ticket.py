from django.db import models
from django.db.models import F
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from base.models import User
from .product import Product
from .quota import Quota


class Ticket(models.Model):
    ticket_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    is_cancelled = models.BooleanField(default=False)
    order = models.ForeignKey("Order", null=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"Ticket {self.ticket_id} - {self.user.name}"

    def is_active(self):
        return (
            not self.is_cancelled
            and self.order.status == "successful"
            and self.product.is_ticket_active()
        )

    def cancel(self):
        self.is_cancelled = True
        self.save()

    @classmethod
    def get_active_qs(cls):
        # marked either as booked and order as successful
        return (
            cls.objects.filter(is_cancelled=False)
            .filter(order__status="successful")
            .filter(
                product__tickets_active_until__isnull=True,
                product__tickets_active_until__gte=now(),
            )
        )

    @classmethod
    def get_active_tickets_for_user(cls, user):
        return cls.get_active_qs().filter(user=user)

    @classmethod
    def create_tickets(cls, user, order):
        tickets = []
        for _ in range(order.quantity):
            ticket = cls.objects.create(
                user=user,
                product=order.product,
                order=order,
            )
            tickets.append(ticket)
        return tickets
