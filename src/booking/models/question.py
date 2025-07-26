from django.db import models
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.core.validators import RegexValidator, MaxLengthValidator
from django.utils.timezone import make_aware
from datetime import date, time, datetime
from decimal import Decimal, DecimalException
from django.db.models import Q
from django.utils import formats
from .event import Event
from .product import Product
import dateutil.parser
from base.helpers.phone_number import validate_phone_number


class Question(models.Model):
    """
    A question is an input field that can be used to extend a ticket by custom information,
    e.g. "Attendee age". The answers are found next to the position. The answers may be found
    in Answers, attached to Order/Cart. A question can allow one of
    several input types.

    Parameters:
    - question (string): The field label shown to the customer
    - help_text (string): The help text shown to the customer
    - type (string): The expected type of answer. Valid options:
        N - number
        S - one-line string
        T - multi-line string
        B - boolean
        F - file upload
        D - date
        H - time
        W - date and time
        TEL - telephone number
    - required (boolean): If true, the question needs to be filled out.
    - position (integer): An integer, used for sorting
    - products (list of integers): List of product IDs this question is assigned to. Should belong to the same event.
    - all_products (boolean): If true, this question is assigned to all products of the event.
    - hidden (boolean): If true, the question will only be shown in the backend.
    - valid_number_min (string): Minimum value for number questions (optional)
    - valid_number_max (string): Maximum value for number questions (optional)
    - valid_date_min (date): Minimum value for date questions (optional)
    - valid_date_max (date): Maximum value for date questions (optional)
    - valid_datetime_min (datetime): Minimum value for date and time questions (optional)
    - valid_datetime_max (datetime): Maximum value for date and time questions (optional)
    - valid_string_length_max (integer): Maximum length for string questions (optional)
    """

    TYPE_NUMBER = "N"
    TYPE_STRING = "S"
    TYPE_TEXT = "T"
    TYPE_BOOLEAN = "B"
    TYPE_FILE = "F"
    TYPE_DATE = "D"
    TYPE_TIME = "H"
    TYPE_DATETIME = "W"
    TYPE_PHONENUMBER = "TEL"
    TYPE_CHOICES = (
        (TYPE_NUMBER, "Number"),
        (TYPE_STRING, "Text (one line)"),
        (TYPE_TEXT, "Multiline text"),
        (TYPE_BOOLEAN, "Yes/No"),
        (TYPE_FILE, "File upload"),
        (TYPE_DATE, "Date"),
        (TYPE_TIME, "Time"),
        (TYPE_DATETIME, "Date and time"),
        (TYPE_PHONENUMBER, "Phone number"),
    )

    question_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, related_name="questions", on_delete=models.CASCADE)
    question = models.TextField(
        verbose_name="Question",
        help_text="This is the question that will be asked to the buyer.",
    )
    help_text = models.TextField(
        verbose_name="Help text",
        help_text="If the question needs to be explained or clarified, do it here!",
        null=True,
        blank=True,
    )
    type = models.CharField(
        max_length=5,
        choices=TYPE_CHOICES,
        verbose_name="Question type",
        help_text="""
        The expected type of answer. Valid options:
        N - number
        S - one-line string
        T - multi-line string
        B - boolean
        F - file upload
        D - date
        H - time
        W - date and time
        TEL - telephone number
        """,
    )
    required = models.BooleanField(default=False, verbose_name="Required question")
    can_modify_later = models.BooleanField(
        default=False, verbose_name="Can modify after order is placed"
    )
    products = models.ManyToManyField(
        Product,
        related_name="questions",
        verbose_name=("Products"),
        blank=True,
        help_text=("This question will be asked to buyers of the selected products"),
    )
    all_products = models.BooleanField(
        default=False,
        verbose_name=("All products"),
        help_text=(
            "This question will be asked to buyers of all products in this event. "
            "If you select specific products, this question will only be asked for those."
        ),
    )
    position = models.PositiveIntegerField(default=0, verbose_name=("Position"))
    hidden = models.BooleanField(
        verbose_name=("Hidden question"),
        help_text=("This question will only show up in the backend."),
        default=False,
    )
    valid_number_min = models.DecimalField(
        decimal_places=6,
        max_digits=30,
        null=True,
        blank=True,
        verbose_name=("Minimum value"),
    )
    valid_number_max = models.DecimalField(
        decimal_places=6,
        max_digits=30,
        null=True,
        blank=True,
        verbose_name=("Maximum value"),
    )
    valid_date_min = models.DateField(
        null=True,
        blank=True,
        verbose_name=("Minimum value"),
    )
    valid_date_max = models.DateField(
        null=True,
        blank=True,
        verbose_name=("Maximum value"),
    )
    valid_datetime_min = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=("Minimum value"),
    )
    valid_datetime_max = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=("Maximum value"),
    )
    valid_string_length_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=("Maximum length"),
    )

    class Meta:
        ordering = ("position", "question_id")

    def __str__(self):
        return str(self.question)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.event:
            self.event.cache.clear()

    @property
    def sortkey(self):
        return self.position, self.question_id

    def __lt__(self, other) -> bool:
        return self.sortkey < other.sortkey

    def is_applicable(self, product):
        """
        Check if this question is applicable to the given product. This includes checking if the product
        is in the list of products for this question or if all_products is set to True.
        """
        if not product.event:
            return False
        if self.all_products and product.event == self.event:
            return True
        if product in self.products.all():
            return True
        return False

    def clean_answer(self, answer):
        if self.required:
            if not answer or (
                self.type == Question.TYPE_BOOLEAN
                and answer not in ("true", "True", True)
            ):
                raise ValidationError(
                    ("An answer to this question is required to proceed.")
                )
        if not answer:
            if self.type == Question.TYPE_BOOLEAN:
                return False
            return None

        if self.type == Question.TYPE_BOOLEAN:
            return answer in ("true", "True", True)
        elif self.type == Question.TYPE_NUMBER:
            answer = formats.sanitize_separators(answer)
            answer = str(answer).strip()
            try:
                v = Decimal(answer)
                if self.valid_number_min is not None and v < self.valid_number_min:
                    raise ValidationError("The number is too low.")
                if self.valid_number_max is not None and v > self.valid_number_max:
                    raise ValidationError("The number is too high.")
                return v
            except DecimalException:
                raise ValidationError(("Invalid number input."))
        elif self.type == Question.TYPE_DATE:
            if isinstance(answer, date):
                return answer
            try:
                dt = dateutil.parser.parse(answer).date()
                if self.valid_date_min is not None and dt < self.valid_date_min:
                    raise ValidationError(("Please choose a later date."))
                if self.valid_date_max is not None and dt > self.valid_date_max:
                    raise ValidationError(("Please choose an earlier date."))
                return dt
            except:
                raise ValidationError(("Invalid date input."))
        elif self.type == Question.TYPE_TIME:
            if isinstance(answer, time):
                return answer
            try:
                return dateutil.parser.parse(answer).time()
            except:
                raise ValidationError(("Invalid time input."))
        elif self.type == Question.TYPE_DATETIME and answer:
            if isinstance(answer, datetime):
                return answer
            try:
                dt = dateutil.parser.parse(answer)
            except:
                raise ValidationError(("Invalid datetime input."))
            else:
                if self.valid_datetime_min is not None and dt < self.valid_datetime_min:
                    raise ValidationError(("Please choose a later date."))
                if self.valid_datetime_max is not None and dt > self.valid_datetime_max:
                    raise ValidationError(("Please choose an earlier date."))
                return dt
        elif self.type == Question.TYPE_PHONENUMBER:
            if not validate_phone_number(answer):
                raise ValidationError(("Invalid phone number."))
            return answer
        elif self.type in (Question.TYPE_STRING, Question.TYPE_TEXT):
            if (
                self.valid_string_length_max is not None
                and len(answer) > self.valid_string_length_max
            ):
                raise ValidationError(
                    MaxLengthValidator.message
                    % {
                        "limit_value": self.valid_string_length_max,
                        "show_value": len(answer),
                    }
                )

        return answer

    @classmethod
    def get_questions_for_product(cls, product, only_required=False):
        """
        Get all questions for a product. This includes questions that are set to be asked for all products.
        """
        if not product.event:
            return cls.objects.none()
        questions = cls.objects.filter(
            Q(products=product) | Q(all_products=True),
            event=product.event,
            hidden=False,
        )
        if only_required:
            questions = questions.filter(required=True)
        questions = questions.distinct()
        return questions
