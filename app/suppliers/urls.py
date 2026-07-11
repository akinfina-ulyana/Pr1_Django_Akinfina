from rest_framework.routers import DefaultRouter

from suppliers.views import (
    SupplierInventoryViewSet,
    SupplierPromotionItemViewSet,
    SupplierPromotionViewSet,
    SupplierViewSet,
)


router = DefaultRouter()

router.register(
    "supplier-inventory",
    SupplierInventoryViewSet,
    basename="supplier-inventory",
)
router.register(
    "supplier-promotions",
    SupplierPromotionViewSet,
    basename="supplier-promotion",
)
router.register(
    "supplier-promotion-items",
    SupplierPromotionItemViewSet,
    basename="supplier-promotion-item",
)
router.register("", SupplierViewSet, basename="supplier")
urlpatterns = router.urls
