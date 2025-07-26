import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from razexOne.storages import PublicMediaStorage
from django.core.validators import MinValueValidator


class EventCity(models.Model):
    city_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    is_top_city = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} <{self.city_id}>"

    @classmethod
    def get_top_cities(cls):
        return cls.objects.filter(is_top_city=True)


class EventCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to="categories/", storage=PublicMediaStorage, blank=True, null=True
    )
    is_top_category = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    @classmethod
    def get_top_categories(cls):
        return cls.objects.filter(is_top_category=True)


class Subcategory(models.Model):
    subcategory_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        EventCategory, on_delete=models.CASCADE, related_name="subcategories"
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return f"{self.name} - {self.category.name}"


class VenueLayout(models.Model):
    layout_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to="venue_layouts/", storage=PublicMediaStorage, blank=True, null=True
    )
    image_height = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(0)]
    )
    image_width = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"Layout <{self.name}>"


class VenueLayoutSection(models.Model):
    section_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    layout = models.ForeignKey(VenueLayout, on_delete=models.CASCADE)
    coordinates = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.layout.name}"


class Artist(models.Model):
    artist_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to="artists/", storage=PublicMediaStorage, blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)
    spotify_link = models.URLField(blank=True, null=True)
    youtube_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Event(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    hero_image = models.ImageField(
        upload_to="events/", storage=PublicMediaStorage, blank=True, null=True
    )
    position = models.PositiveIntegerField(default=0)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    sale_start = models.DateTimeField()
    sale_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    cities = models.ManyToManyField(EventCity, related_name="events", blank=True)
    categories = models.ManyToManyField(
        EventCategory, related_name="events", blank=True
    )
    subcategories = models.ManyToManyField(
        Subcategory, related_name="events", blank=True
    )
    artists = models.ManyToManyField(Artist, related_name="events", blank=True)
    layout = models.ForeignKey(
        VenueLayout, on_delete=models.SET_NULL, null=True, default=None
    )
    is_featured = models.BooleanField(default=False)
    price_start = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, default=None
    )
    price_end = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, default=None
    )
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    highlights = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    tac = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["position", "start_date"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        # Make sure sale_start is before sale_end
        if self.sale_start and self.sale_end and self.sale_start > self.sale_end:
            raise ValidationError("Sale start date must be before sale end date")
        # Make sure start_date is before end_date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Event start date must be before event end date")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_subevents(self):
        return SubEvent.objects.filter(event=self)

    def is_sale_active(self):
        """Check if tickets/products can be purchased."""
        if not self.is_active:
            return False
        _now = now()
        sale_start = self.sale_start or _now
        sale_end = self.sale_end or _now
        return sale_start <= _now <= sale_end


class EventImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to="event_images/", storage=PublicMediaStorage)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="images")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Image <{self.image_id}> - {self.event.name}"

    @classmethod
    def get_active_images(cls, event):
        return cls.objects.filter(event=event, is_active=True)


class Subevent(models.Model):
    subevent_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    hero_image = models.ImageField(
        upload_to="subevents/", storage=PublicMediaStorage, blank=True, null=True
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="subevents")
    city = models.ForeignKey(
        EventCity, on_delete=models.SET_NULL, null=True, default=None
    )

    def clean(self):
        # Make sure start_date is before end_date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Subevent start date must be before subevent end")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.event.name}"


class IteneraryItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    title = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="itenerary")
    subevent = models.ForeignKey(
        Subevent,
        on_delete=models.CASCADE,
        related_name="itenerary",
        null=True,
        default=None,
    )
    date = models.DateTimeField()

    def __str__(self):
        return f"{self.title} - {self.event.name}"

    class Meta:
        ordering = ["date"]

    @classmethod
    def get_itenerary(cls, event):
        return cls.objects.filter(event=event)
