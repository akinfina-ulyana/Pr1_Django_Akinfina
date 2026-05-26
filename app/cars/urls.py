from rest_framework.routers import DefaultRouter

from .views import CarModelViewSet


router = DefaultRouter()
router.register(r"", CarModelViewSet, basename="cars")

urlpatterns = router.urls
