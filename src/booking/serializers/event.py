from rest_framework import serializers
from booking.models import (
    EventCity,
    EventCategory,
    VenueLayoutSection,
    VenueLayout,
    Event,
    Product,
    Subevent,
    Artist,
    IteneraryItem,
    Subcategory,
    EventImage,
)

from .product import ProductSerializer


class EventCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCity
        fields = "__all__"


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = "__all__"


class ArtistListedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ["artist_id", "name", "image"]


class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = "__all__"


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = "__all__"


class EventCategoryDetailSerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True)

    class Meta:
        model = EventCategory
        fields = "__all__"


class VenueLayoutSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueLayoutSection
        fields = "__all__"


class VenueLayoutBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueLayout
        fields = "__all__"


class VenueLayoutSerializer(VenueLayoutBaseSerializer):
    sections = VenueLayoutSectionSerializer(many=True, source="venuelayoutsection_set")

    class Meta:
        model = VenueLayout
        fields = "__all__"


class SubeventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subevent
        fields = "__all__"


class EventBaseSerializer(serializers.ModelSerializer):
    is_sale_active = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = "__all__"

    def get_is_sale_active(self, obj):
        return obj.is_sale_active()

    def validate(self, data):
        # Make sure subcategories belong to the selected categories
        event = self.instance
        categories = data.get("categories", None)
        if categories is None:
            if event is None:
                return data
            categories = event.categories.all()
        subcategories = data.get("subcategories", [])
        category_ids = [category.category_id for category in categories]
        for subcategory in subcategories:
            if subcategory.category.category_id not in category_ids:
                raise serializers.ValidationError(
                    f"Subcategory {subcategory.name} does not belong to any selected category"
                )

        return super().validate(data)

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     request = self.context.get("request", None)
    #     if not (request and getattr(request.user, "is_staff", False)):
    #         for field in ["sale_start", "sale_end", "is_active"]:
    #             representation.pop(field, None)
    #     return representation


END_USER_EVENT_EXCLUDE_FIELDS = [
    "created_at",
    "updated_at",
    "is_active",
    "tac",
    "position",
    "subcategories",
]


class EventListedSerializer(EventBaseSerializer):
    categories = EventCategorySerializer(many=True)
    cities = EventCitySerializer(many=True)

    class Meta:
        model = Event
        exclude = END_USER_EVENT_EXCLUDE_FIELDS + [
            "layout",
            "artists",
            "highlights",
            "subtitle",
            "address",
        ]


class EventDetailSerializer(EventListedSerializer):
    subevents = SubeventSerializer(many=True)
    layout = VenueLayoutSerializer()
    artists = ArtistListedSerializer(many=True)

    class Meta:
        model = Event
        exclude = END_USER_EVENT_EXCLUDE_FIELDS


class AdminEventDetailSerializer(EventDetailSerializer):

    class Meta:
        model = Event
        fields = "__all__"


class IteneraryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IteneraryItem
        fields = "__all__"

    def validate(self, attrs):
        # Verify subevent belongs to the event
        itenary_item = self.instance
        event = attrs.get("event", itenary_item.event if itenary_item else None)
        subevent = attrs.get("subevent", None)
        if subevent and event and subevent.event.event_id != event.event_id:
            raise serializers.ValidationError("Subevent must belong to the event")
        return super().validate(attrs)


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = "__all__"


class CatalogSectionSerializer(serializers.Serializer):
    subcategory = SubcategorySerializer()
    events = EventListedSerializer(many=True)
