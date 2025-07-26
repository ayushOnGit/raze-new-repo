from django.db import models
from django.db.models import F, Q
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from base.models import User
from razexOne.storages import PrivateMediaStorage
from .product import Product
from .ticket import Ticket
from .promotion import Promotion
from .quota import Quota
from razexOne.settings import (
    PLATFORM_FEE,
    TAX_RATE,
    MIN_WALLET_RECHARGE,
    MAX_WALLET_RECHARGE,
    WALLET_PAYMENT_GATEWAY,
)
from base.models import Wallet
from base.helpers.code import generate_coupon_code
import decimal
from django.core.validators import MinValueValidator
from django.utils.formats import date_format
from django.utils.timezone import now
import dateutil.parser
from django.utils.timezone import now
from django.utils.timezone import timedelta
from .question import Question


TAX_RATE = decimal.Decimal(TAX_RATE)
PLATFORM_FEE = decimal.Decimal(PLATFORM_FEE)


def get_default_expiry():
    return now() + timedelta(minutes=30)


class Answer(models.Model):
    """
    The answer to a Question, connected to an Order or Cart.

    :param order: The order this is related to, or null if this is related to a cart.
    :type order: Order
    :param cart: The cart this is related to, or null if this is related to an order.
    :type cart: Cart
    :param question: The question this is an answer for
    :type question: Question
    :param answer: The actual answer data
    :type answer: str
    """

    answer_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        "Order",
        null=True,
        blank=True,
        related_name="answers",
        on_delete=models.CASCADE,
    )
    cart = models.ForeignKey(
        "Cart",
        null=True,
        blank=True,
        related_name="answers",
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        Question, related_name="answers", on_delete=models.CASCADE
    )
    answer = models.TextField(blank=True)
    file = models.FileField(
        upload_to="answers/", storage=PrivateMediaStorage, blank=True, null=True
    )

    class Meta:
        unique_together = [["order", "question"], ["cart", "question"]]

    @property
    def file_name(self):
        return self.file.name.split(".", 1)[-1]

    def __str__(self):
        return self.to_string(use_cached=True)

    def to_string(self, use_cached=True):
        """
        Render this answer as a string.

        :param use_cached: If ``True`` (default), choice and multiple choice questions will show their cached
        value, i.e. the value of the selected options at the time of saving and in the language
        the answer was saved in. If ``False``, the values will instead be loaded from the
        database, yielding current and translated values of the options. However, additional database
        queries might be required.
        """
        if self.question.type == Question.TYPE_BOOLEAN and self.answer == "True":
            return str("Yes")
        elif self.question.type == Question.TYPE_BOOLEAN and self.answer == "False":
            return str("No")
        elif self.question.type == Question.TYPE_FILE:
            return str("<file>")
        elif self.question.type == Question.TYPE_DATETIME and self.answer:
            try:
                d = dateutil.parser.parse(self.answer)
                return date_format(d, "SHORT_DATETIME_FORMAT")
            except ValueError:
                return self.answer
        elif self.question.type == Question.TYPE_DATE and self.answer:
            try:
                d = dateutil.parser.parse(self.answer)
                return date_format(d, "SHORT_DATE_FORMAT")
            except ValueError:
                return self.answer
        elif self.question.type == Question.TYPE_TIME and self.answer:
            try:
                d = dateutil.parser.parse(self.answer)
                return date_format(d, "TIME_FORMAT")
            except ValueError:
                return self.answer
        elif (
            self.question.type in (Question.TYPE_CHOICE, Question.TYPE_CHOICE_MULTIPLE)
            and self.answer
            and not use_cached
        ):
            return ", ".join(str(o.answer) for o in self.options.all())
        else:
            return self.answer

    def save(self, *args, **kwargs):
        if self.order and self.cart:
            raise ValueError(
                "Answer cannot be linked to an order and a cart at the same time."
            )
        if not self.order and not self.cart:
            raise ValueError("Answer must be linked to either an order or a cart.")
        super().save(*args, **kwargs)

    @classmethod
    def move_to_order(cls, order, cart):
        """
        Move all answers from a cart to an order.

        :param order: The order to move the answers to.
        :type order: Order
        :param cart: The cart to move the answers from.
        :type cart: Cart
        """
        answers = cls.objects.filter(cart=cart)
        for answer in answers:
            answer.order = order
            answer.cart = None
            answer.save()
        return answers


class PaymentMode(models.TextChoices):
    ONLINE = "online", "Online"
    WALLET = "wallet", "Wallet"


class OrderType(models.TextChoices):
    TICKET = "ticket", "Ticket"
    COUPON = "coupon", "Coupon"
    WALLET_RECHARGE = "wallet_recharge", "Wallet Recharge"


class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    discount_coupon = models.CharField(max_length=50, null=True, blank=True)
    expires_on = models.DateTimeField(default=get_default_expiry)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    # Gross price - discount + tax + fees = net price.
    net_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    gross_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=PLATFORM_FEE,
        validators=[MinValueValidator(0)],
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    end_user_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("initial", "Initial"),
            ("freed", "Freed"),
            ("order_created", "Order Created"),
        ],
    )
    order = models.OneToOneField(
        "Order", null=True, blank=True, on_delete=models.SET_NULL
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.ONLINE,
    )
    applied_promo_ids = models.JSONField(null=True, blank=True)
    is_promoter = models.BooleanField(default=False)

    def __str__(self):
        return f"Cart {self.cart_id} - {self.user.name}"

    def assert_product(self):
        if not self.product:
            raise ValidationError("Product is unavailable.")

    def is_expired(self):
        return self.expires_on <= now() or self.status == "freed"

    def can_modify(self):
        return self.status == "initial" and not self.is_expired()

    def has_required_answers(self):
        if not self.product:
            return True
        questions = Question.get_questions_for_product(self.product, only_required=True)
        if not questions.exists():
            return True
        answers = Answer.objects.filter(cart=self, question__in=questions)
        return answers.count() >= questions.count()

    def get_questions(self):
        if not self.product:
            Question.objects.none()
        questions = Question.get_questions_for_product(self.product)
        return questions

    def calculate_pricing(self):
        self.assert_product()
        self.gross_price = self.product.price * self.quantity

        # Fetch and apply promotions
        net_price, promo_ids, end_user_discount_percentage = Promotion.apply_promotions(
            self
        )
        self.discount_amount = self.gross_price - net_price
        self.applied_promo_ids = promo_ids
        self.end_user_discount_percentage = end_user_discount_percentage

        # Apply platform fee
        self.platform_fee = PLATFORM_FEE if net_price > 0 else 0
        net_price += self.platform_fee

        # Apply tax
        self.tax = TAX_RATE * net_price
        net_price += self.tax

        self.net_price = net_price
        self.save()

    def apply_coupon(self, coupon_code=None):
        if not self.can_modify():
            raise ValidationError("Cart is no longer valid.")
        with transaction.atomic():
            self.discount_coupon = coupon_code
            self.calculate_pricing()

    def change_quantity(self, quantity):
        if not self.product.is_sale_active():
            raise ValidationError("Product is not available for sale.")
        with transaction.atomic():
            if not self.can_modify():
                raise ValidationError("Cart is no longer valid.")
            self.quantity = quantity
            # todo: add quantity to availability check.
            self.calculate_pricing()

    def change_payment_mode(self, payment_mode):
        self.assert_product()
        with transaction.atomic():
            if not self.can_modify():
                raise ValidationError("Cart is no longer valid.")
            self.payment_mode = payment_mode
            self.calculate_pricing()

    def cancel_cart(self):
        with transaction.atomic():
            if not self.can_modify():
                raise ValidationError("Cart is no longer valid.")
            self.status = "freed"
            self.save()

    def get_order_type(self):
        if self.is_promoter:
            return OrderType.COUPON
        return OrderType.TICKET

    @classmethod
    def create_cart(cls, user, product, quantity, is_promoter=False):
        cart = cls.objects.create(
            user=user,
            status="initial",
            product=product,
            quantity=quantity,
            is_promoter=is_promoter,
        )
        cart.calculate_pricing()
        return cart

    @classmethod
    def lock_cart(cls, cart_id, user):
        return cls.objects.select_for_update().get(pk=cart_id, user=user)

    @classmethod
    def clear_expired_carts(cls, max_count=500):
        with transaction.atomic():
            carts = cls.objects.select_for_update(skip_locked=True).filter(
                status="initial", expires_on__lte=now()
            )
            carts = carts[:max_count]
            for cart in carts:
                cart.cancel_cart()
            return carts


class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)
    expiry_on = models.DateTimeField(default=get_default_expiry)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(null=True)
    net_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )  # net price
    gross_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )  # gross price
    tax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    platform_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    discount_coupon = models.CharField(max_length=50, null=True, blank=True)
    payment_id = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("initial", "Initial"),
            ("failed", "Failed"),
            ("successful", "Successful"),
        ],
        default="initial",
    )
    failure_reason = models.TextField(null=True, blank=True)
    payment_gateway = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.TICKET,
    )
    applied_quota_ids = models.JSONField(null=True, blank=True)
    end_user_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True
    )

    # Validate quanitity and price before saving
    def clean(self):
        if self.type == OrderType.TICKET or self.type == OrderType.COUPON:
            if self.quantity <= 0:
                raise ValidationError("Quantity must be greater than 0.")
            if self.product is None:
                raise ValidationError("Product is required for this order.")
        elif self.type == OrderType.WALLET_RECHARGE:
            if self.payment_gateway == WALLET_PAYMENT_GATEWAY:
                raise ValidationError("Cannot recharge wallet using wallet.")
            self.quantity = None
            self.product = None
            if self.gross_price < MIN_WALLET_RECHARGE:
                raise ValidationError(
                    f"Minimum recharge amount is {MIN_WALLET_RECHARGE}."
                )
            if self.gross_price > MAX_WALLET_RECHARGE:
                raise ValidationError(
                    f"Maximum recharge amount is {MAX_WALLET_RECHARGE}."
                )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_id} - {self.user.name}"

    def is_expired(self):
        return self.expiry_on <= now()

    def is_failed(self):
        return self.status == "failed"

    def is_active(self):
        return not self.is_failed() and not self.is_expired()

    def get_tickets(self):
        return Ticket.objects.filter(order=self)

    def has_payment(self):
        return self.net_price >= 1 and self.payment_id is not None

    def cancel_order(self, reason="Cancelled"):
        if not self.is_failed():
            return False
        if self.status == "successful":
            raise ValidationError("Cannot cancel this order.")
        with transaction.atomic():
            self.status = "failed"
            self.failure_reason = reason
            self.save()

            if self.applied_quota_ids:
                # Release quota slots atomically
                quotas = Quota.objects.filter(
                    quota_id__in=self.applied_quota_ids
                ).select_for_update()
                for quota in quotas:
                    try:
                        quota.slots_booked = F("slots_booked") - self.quantity
                        quota.save()
                    except Exception as e:
                        # We are not raising an error here as we want to continue with the cancellation.
                        # But if we find this error, we should investigate and fix the underlying issue.
                        # Mostly the save might fail if the quota numbers are not in sync or has been manually modified.
                        print(
                            f"Failed to release quota slots for order {self.order_id}: {e}"
                        )

            if self.type == OrderType.TICKET:
                # Cancel tickets
                self.cancel_tickets()
            return True

    @classmethod
    def create_order(cls, cart, payment_id=None, payment_gateway=None):
        with transaction.atomic():
            cart.assert_product()
            if not cart.can_modify():
                raise ValidationError("Cart is no longer valid.")

            # Check if product is still active for sale
            if not cart.product.is_sale_active():
                raise ValidationError("Product is not available for sale.")

            product_id = cart.product.product_id
            promo_ids = cart.applied_promo_ids
            # Make sure all the promo_ids are still active before proceeding
            if promo_ids:
                promos = Promotion.get_active_promotions(cart.product.event).filter(
                    promo_id__in=promo_ids
                )
                if promos.count() != len(promo_ids):
                    raise ValidationError(
                        "Some promotions are no longer valid. Please refresh cart."
                    )

            # Check if all questions have been answered
            if not cart.has_required_answers():
                raise ValidationError("Please answer all required questions.")

            deduct_product_quota = True

            # Check if we need to deduct product quota slots
            # If there is a promoter created discount coupon, we don't need to deduct product quota slots
            # Since slots for these tickets have already been deducted when the coupon was created

            if cart.discount_coupon:
                promo = Promotion.get_promotion_by_code(cart.discount_coupon)
                deduct_product_quota = not promo or not promo.promo_owner

            # Lock quotas to avoid race conditions
            # Setting no_key to let other models add reference to quotas even during transaction

            filter_query = Q(promo__promo_id__in=promo_ids)
            if deduct_product_quota:
                filter_query |= Q(products__product_id=product_id)

            quotas = Quota.objects.filter(filter_query).select_for_update(
                no_key=True, of=("self")
            )

            # Check quota availability and reserve slots atomically
            for quota in quotas:
                to_be_booked = cart.quantity
                if quota.get_remaining_slots() < to_be_booked:
                    raise ValidationError("Not enough quota available.")
                quota.slots_booked = F("slots_booked") + to_be_booked  # Atomic update
                quota.save()

            order = cls.objects.create(
                user=cart.user,
                net_price=cart.net_price,
                gross_price=cart.gross_price,
                tax=cart.tax,
                platform_fee=cart.platform_fee,
                discount_amount=cart.discount_amount,
                product=cart.product,
                quantity=cart.quantity,
                discount_coupon=cart.discount_coupon,
                payment_id=payment_id,
                payment_gateway=payment_gateway,
                type=cart.get_order_type(),
                applied_quota_ids=[quota.quota_id for quota in quotas],
                end_user_discount_percentage=cart.end_user_discount_percentage,
            )

            cart.status = "order_created"
            cart.order = order
            cart.save()

            # Move answers from cart to order
            Answer.move_to_order(order, cart)

            # Confirm automatically if payment is not required
            if not order.has_payment():
                order.confirm_payment()
            return order

    @classmethod
    def create_wallet_recharge_order(
        cls, user, amount, payment_id=None, payment_gateway=None
    ):
        with transaction.atomic():
            order = cls.objects.create(
                user=user,
                net_price=amount,
                gross_price=amount,
                tax=0,
                platform_fee=0,
                discount_amount=0,
                type=OrderType.WALLET_RECHARGE,
                payment_id=payment_id,
                payment_gateway=payment_gateway,
            )
            return order

    def create_promotion(self):
        promo = Promotion.objects.create(
            event=self.product.event,
            promo_owner=self.user,
            code=generate_coupon_code(),
            all_products=False,
            discount_percentage=self.end_user_discount_percentage,
            name=f"Exclusive discount of {self.end_user_discount_percentage}%",
            products=[self.product],
            is_listed=False,
        )
        quota = Quota.objects.create(
            name=f"Promotion for {self.product.name}",
            max_count=self.quantity,
            promo=promo,
        )

    def payout_to_promo_owner(self):
        promo = Promotion.get_promotion_by_code(self.discount_coupon)
        if not promo or not promo.promo_owner:
            return False
        discount_percentage = promo.end_user_discount_percentage or 0
        payout_percentage = 100 - discount_percentage
        payout_amount = self.gross_price * (payout_percentage / 100)
        wallet = Wallet.get_wallet_for_user(promo.promo_owner)
        wallet.credit(
            payout_amount,
            f"Refund from coupon sales for ${self.product.event.name} - {self.product.name}",
        )
        return True

    def confirm_payment(self):
        if self.status == "successful":
            False
        with transaction.atomic():
            if self.status != "initial" or self.is_expired():
                raise ValidationError("Order is no longer valid.")
            self.status = "successful"
            # todo: send confirmation email
            if self.type == OrderType.TICKET:
                tickets = Ticket.create_tickets(self.user, self)
                if self.discount_coupon:
                    self.payout_to_promo_owner()
            elif self.type == OrderType.COUPON:
                self.create_promotion()
            elif self.type == OrderType.WALLET_RECHARGE:
                wallet = Wallet.get_or_create_wallet(self.user)
                wallet.credit(self.gross_price, "Wallet recharge")
            self.save()
            return True

    def cancel_tickets(self, quantity=None):
        with transaction.atomic():
            tickets = Ticket.objects.select_for_update().filter(order=self)
            if quantity is not None:
                tickets = tickets[:quantity]
            for ticket in tickets:
                ticket.cancel()
            return tickets

    @classmethod
    def lock_order(cls, order_id, user):
        return cls.objects.select_for_update().get(pk=order_id, user=user)

    @classmethod
    def clear_expired_orders(cls, max_count=500):
        with transaction.atomic():
            orders = cls.objects.select_for_update(skip_locked=True).filter(
                status="initial", expiry_on__lte=now()
            )
            orders = orders[:max_count]
            for order in orders:
                try:
                    order.cancel("Expired")
                except Exception as e:
                    print(f"Failed to cancel expired order {order.order_id}: {e}")
            return orders
