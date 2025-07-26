from rest_framework import viewsets, serializers, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from booking.models import (
    Event,
    EventCity,
    EventCategory,
    VenueLayoutSection,
    VenueLayout,
    Artist,
    Subevent,
    IteneraryItem,
    Subcategory,
    EventImage,
)
from booking.serializers.event import (
    EventBaseSerializer,
    EventListedSerializer,
    EventDetailSerializer,
    EventCitySerializer,
    EventCategorySerializer,
    VenueLayoutSectionSerializer,
    VenueLayoutSerializer,
    VenueLayoutBaseSerializer,
    SubeventSerializer,
    ArtistSerializer,
    AdminEventDetailSerializer,
    IteneraryItemSerializer,
    ArtistListedSerializer,
    SubcategorySerializer,
    EventCategoryDetailSerializer,
    EventImageSerializer,
    CatalogSectionSerializer,
)
from booking.filters.event import EventFilter
from base.helpers.api_permissions import AdminPermission
from rest_framework import exceptions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status
from rest_framework.response import Response
from razexOne.settings import EVENT_TAC
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from django.shortcuts import get_object_or_404


def _get_event_queryset(action, active_only=True):
    queryset = (
        Event.objects.all().prefetch_related("categories").prefetch_related("cities")
    )
    if active_only:
        queryset = queryset.filter(is_active=True)
    if action == "retrieve":
        queryset = queryset.prefetch_related("subevents").select_related("layout")
    return queryset


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventListedSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = EventFilter
    ordering_fields = ["start_date"]
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EventDetailSerializer
        return EventListedSerializer

    def get_queryset(self):
        # Fix for swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Event.objects.none()

        queryset = _get_event_queryset(self.action)
        return queryset

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "city",
                openapi.IN_QUERY,
                description="City ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                description="Category ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of sections",
                schema=CatalogSectionSerializer(many=True),
            )
        },
    )
    @action(detail=False, methods=["get"])
    def catalog(self, request, *args, **kwargs):
        """
        Expects a city and a category and returns a curated list of events
        grouped into sections to be displayed in the home page. Ignore other parameters, they wont work.
        """
        city_id = request.query_params.get("city")
        category_id = request.query_params.get("category")

        if not category_id:
            raise exceptions.ValidationError("city or category is required")

        category = get_object_or_404(EventCategory, pk=category_id)
        city = None

        if city_id:
            city = get_object_or_404(EventCity, pk=city_id)

        subcategories = Subcategory.objects.filter(category=category).distinct()
        if not subcategories.exists():
            raise exceptions.ValidationError("No subcategories found for this category")

        subcategories = subcategories[:15]  # Limit to 15 subcategories

        resp = list()

        for subcategory in subcategories:
            section = dict()
            section["subcategory"] = SubcategorySerializer(subcategory).data
            section["events"] = list()
            events = _get_event_queryset("list").filter(subcategories=subcategory)
            if city:
                events = events.filter(cities=city)
            events = events.distinct()
            events = events[:20]  # Limit to 20 events
            section["events"] = EventListedSerializer(events, many=True).data
            resp.append(section)

        return Response(resp)

    @swagger_auto_schema(
        operation_description="Terms and conditions for the event.",
    )
    @action(detail=True, methods=["get"])
    def terms_and_conditions(self, request, *args, **kwargs):
        event = self.get_object()
        if not event.tac:
            return Response(EVENT_TAC)
        return Response(event.tac)

    """
    Get event images.
    """

    @swagger_auto_schema(
        operation_description="Get event images.",
    )
    @action(detail=True, methods=["get"])
    def images(self, request, *args, **kwargs):
        event = self.get_object()
        images = EventImage.get_active_images(event=event)
        serializer = EventImageSerializer(images, many=True)
        return Response(serializer.data)


class EventCityListViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_top_city"]
    queryset = EventCity.objects.all()
    serializer_class = EventCitySerializer
    search_fields = ["name"]


class EventCategoryListViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_top_category"]
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EventCategoryDetailSerializer
        return EventCategorySerializer


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ArtistListedSerializer
        return ArtistSerializer


# Admin ViewSets


class AdminEventViewSet(viewsets.ModelViewSet):
    """
    Adding multiple categories, subcategories etc. does not work currently in swagger.
    There is an issue with the swagger schema generation, the generated curl send these fields as comma separated values which is not supported by the API.
    The APIs expect the fields to be sent as repeated fields.
    For example:
    -F 'categories=1' -F 'categories=2' -F 'categories=3' instead of -F 'categories=1,2,3'
    As a workaround, copy the curl command to insomnia and change the fields to be repeated fields.
    """

    queryset = Event.objects.all()
    serializer_class = EventBaseSerializer
    permission_classes = [AdminPermission]
    parser_classes = (FormParser, MultiPartParser)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminEventDetailSerializer
        elif self.action == "list":
            return EventListedSerializer
        return EventBaseSerializer

    def get_queryset(self):
        return _get_event_queryset(self.action, active_only=False)


class AdminSubeventViewSet(viewsets.ModelViewSet):
    queryset = Subevent.objects.all()
    serializer_class = SubeventSerializer
    permission_classes = [AdminPermission]


class AdminEventCityViewSet(viewsets.ModelViewSet):
    queryset = EventCity.objects.all()
    serializer_class = EventCitySerializer
    permission_classes = [AdminPermission]


class AdminEventCategoryViewSet(viewsets.ModelViewSet):
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [AdminPermission]
    parser_classes = (FormParser, MultiPartParser)


class AdminSubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
    permission_classes = [AdminPermission]


class AdminArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [AdminPermission]
    parser_classes = (FormParser, MultiPartParser)


class AdminVenueLayoutSectionViewSet(viewsets.ModelViewSet):
    queryset = VenueLayoutSection.objects.all()
    serializer_class = VenueLayoutSectionSerializer
    permission_classes = [AdminPermission]

    def list(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed("GET")

    def get_queryset(self):
        if self.action == "list":
            return (
                VenueLayoutSection.objects.none()
            )  # Prevents listing in schema generation
        return super().get_queryset()


class AdminVenueLayoutViewSet(viewsets.ModelViewSet):
    queryset = VenueLayout.objects.all()
    serializer_class = VenueLayoutBaseSerializer
    permission_classes = [AdminPermission]
    parser_classes = (FormParser, MultiPartParser)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return VenueLayoutSerializer
        return VenueLayoutBaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            queryset = queryset.prefetch_related("venuelayoutsection_set")
        return queryset


class _SharedItenaryItemViewSet:

    def list(self, request, *args, **kwargs):
        # Make sure that the event_id or subevent_id is provided
        event_id = request.query_params.get("event")
        subevent_id = request.query_params.get("subevent")
        if not event_id and not subevent_id:
            raise exceptions.ValidationError("event or subevent is required")
        return super().list(request, *args, **kwargs)


class AdminIteneraryItemViewSet(_SharedItenaryItemViewSet, viewsets.ModelViewSet):
    queryset = IteneraryItem.objects.all()
    serializer_class = IteneraryItemSerializer
    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["subevent", "event"]


class IteneraryItemViewSet(_SharedItenaryItemViewSet, viewsets.ReadOnlyModelViewSet):
    queryset = IteneraryItem.objects.all()
    serializer_class = IteneraryItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["subevent", "event"]


class AdminEventImageViewSet(viewsets.ModelViewSet):
    queryset = EventImage.objects.all()
    serializer_class = EventImageSerializer
    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    parser_classes = (FormParser, MultiPartParser)
    filterset_fields = ["event"]
    search_fields = ["event__name"]
