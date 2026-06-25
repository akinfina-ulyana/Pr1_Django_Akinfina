from django.urls import path

from rest_framework.routers import DefaultRouter

from buyers.views import BuyerProfileViewSet, DealershipMarketplaceViewSetForBuyers, OfferCreateView


router = DefaultRouter()
router.register("", BuyerProfileViewSet, basename="buyer")
router.register("marketplace", DealershipMarketplaceViewSetForBuyers, basename="marketplace")


urlpatterns = [path("offers/", OfferCreateView.as_view(), name="offer-create"), *router.urls]
