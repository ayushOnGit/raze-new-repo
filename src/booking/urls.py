from django.urls import path
from rest_framework import routers
from .views.event import (
    EventViewSet,
    EventCityListViewSet,
    EventCategoryListViewSet,
    AdminEventViewSet,
    AdminEventCityViewSet,
    AdminEventCategoryViewSet,
    AdminVenueLayoutSectionViewSet,
    AdminVenueLayoutViewSet,
    AdminArtistViewSet,
    ArtistViewSet,
    AdminSubeventViewSet,
    AdminIteneraryItemViewSet,
    IteneraryItemViewSet,
    AdminSubcategoryViewSet,
    AdminEventImageViewSet,
)
from .views.product import AdminProductViewSet, AdminQuotaViewSet, ProductViewSet
from .views.order import (
    CartViewSet,
    OrderViewSet,
    TicketViewSet,
    AdminOrderViewSet,
    AdminTicketViewSet,
    AnswerViewSet,
)
from .views.webhook import WebhookViewSet
from .views.payout import WalletPayoutViewSet
from .views.promotion import AdminPromotionViewSet, OwnerPromotionViewSet, ProductPromotionViewSet
from .views.question import AdminQuestionViewSet

router = routers.DefaultRouter()

# Event and Venue
router.register(r"events", EventViewSet, basename="events")
router.register(r"cities", EventCityListViewSet)
router.register(r"categories", EventCategoryListViewSet)
router.register(r"artists", ArtistViewSet)
router.register(r"itenerary", IteneraryItemViewSet)

router.register(r"admin/events", AdminEventViewSet, basename="admin-events")
router.register(
    r"admin/event-images", AdminEventImageViewSet, basename="admin-event-images"
)
router.register(r"admin/subevents", AdminSubeventViewSet, basename="admin-subevents")

router.register(r"admin/artists", AdminArtistViewSet, basename="admin-artists")
router.register(r"admin/cities", AdminEventCityViewSet, basename="admin-cities")
router.register(
    r"admin/categories", AdminEventCategoryViewSet, basename="admin-categories"
)
router.register(
    r"admin/subcategories", AdminSubcategoryViewSet, basename="admin-subcategories"
)
router.register(
    r"admin/venue/layout", AdminVenueLayoutViewSet, basename="admin-venue-layout"
)
router.register(
    r"admin/venue/layout-section",
    AdminVenueLayoutSectionViewSet,
    basename="admin-venue-layout-section",
)
router.register(
    r"admin/itenerary", AdminIteneraryItemViewSet, basename="admin-itenerary"
)

# Product and Quota
router.register(r"products", ProductViewSet, basename="products")
router.register(r"admin/products", AdminProductViewSet, basename="admin-products")
router.register(r"admin/quotas", AdminQuotaViewSet, basename="admin-quotas")

# Carts and Orders
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"answer", AnswerViewSet, basename="answer")
router.register(r"order", OrderViewSet, basename="order")
router.register(r"ticket", TicketViewSet, basename="ticket")
router.register(r"admin/orders", AdminOrderViewSet, basename="admin-order")
router.register(r"admin/tickets", AdminTicketViewSet, basename="admin-ticket")
router.register(r"admin/questions", AdminQuestionViewSet, basename="admin-question")

# Webhooks
router.register(r"webhook", WebhookViewSet, basename="webhook")

# Payouts
router.register(r"payout", WalletPayoutViewSet, basename="payout")

# Promotions
router.register(r"admin/promotions", AdminPromotionViewSet, basename="admin-promotions")
router.register(r"my-promotions", OwnerPromotionViewSet, basename="my-promotions")
router.register(r"promotions", ProductPromotionViewSet, basename="promotions")

urlpatterns = router.urls
