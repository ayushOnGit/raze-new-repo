import django_filters
from booking.models import Event, EventCategory, Subcategory


class EventFilter(django_filters.FilterSet):
    start_date__gte = django_filters.DateFilter(
        field_name="start_date", lookup_expr="gte"
    )  # Greater than
    start_date__lte = django_filters.DateFilter(
        field_name="start_date", lookup_expr="lte"
    )  # Less than
    end_date__gte = django_filters.DateFilter(field_name="end_date", lookup_expr="gte")
    end_date__lte = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")
    on_date = django_filters.DateFilter(method="filter_on_date")

    categories = django_filters.ModelMultipleChoiceFilter(
        queryset=EventCategory.objects.all(),
        field_name="categories",
        to_field_name="category_id",
        conjoined=False  # OR filtering (e.g., events in any selected category)
    )

    subcategories = django_filters.ModelMultipleChoiceFilter(
        queryset=Subcategory.objects.all(),
        field_name="subcategories",
        to_field_name="subcategory_id",
        conjoined=False  # OR filtering (e.g., events in any selected subcategory
    )

    cities = django_filters.ModelMultipleChoiceFilter(
        queryset=EventCategory.objects.all(),
        field_name="cities",
        to_field_name="city_id",
        conjoined=False  # OR filtering (e.g., events in any selected city)
    )

    artists = django_filters.ModelMultipleChoiceFilter(
        queryset=EventCategory.objects.all(),
        field_name="artists",
        to_field_name="artist_id",
        conjoined=False  # OR filtering (e.g., events with any selected artist)
    )

    def filter_on_date(self, queryset, name, value):
        return queryset.filter(start_date__lte=value, end_date__gte=value)

    class Meta:
        model = Event
        fields = ["cities", "categories", "is_featured", "artists", "subcategories"]
