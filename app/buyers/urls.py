from rest_framework.routers import DefaultRouter

from buyers.views import BuyerProfileViewSet


router = DefaultRouter()
router.register("", BuyerProfileViewSet, basename="buyer")

urlpatterns = router.urls
