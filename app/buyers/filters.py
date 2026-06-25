import django_filters
from cars.filters import CarFieldsFilterMixin
from dealership.models import DealershipInventory


class MarketplaceInventoryFilter(CarFieldsFilterMixin, django_filters.FilterSet):
    car_model_path = "car_model"

    price_min = django_filters.NumberFilter(field_name="effective_price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="effective_price", lookup_expr="lte")
    dealership = django_filters.NumberFilter(field_name="dealership_id")

    class Meta:
        model = DealershipInventory
        fields: list[str] = []
