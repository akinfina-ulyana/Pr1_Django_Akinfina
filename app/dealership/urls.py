from rest_framework.routers import DefaultRouter

from dealership.views import (
    DealershipInventoryViewSet,
    DealershipPreferredCarViewSet,
    DealershipPromotionItemViewSet,
    DealershipPromotionViewSet,
    DealershipViewSet,
    PrioritySuppliersViewSet,
)


router = DefaultRouter()

router.register("dealership-inventory", DealershipInventoryViewSet, basename="dealership-inventory")
router.register("dealership-promotions", DealershipPromotionViewSet, basename="dealership-promotion")
router.register("dealership-promotion-items", DealershipPromotionItemViewSet, basename="dealership-promotion-item")
router.register("priority-suppliers", PrioritySuppliersViewSet, basename="priority-supplier")
router.register("dealership-preferred-cars", DealershipPreferredCarViewSet, basename="dealership-preferred-car")
router.register("", DealershipViewSet, basename="dealership")

urlpatterns = router.urls
