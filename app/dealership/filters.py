import django_filters
from cars.filters import CarFieldsFilterMixin

from dealership.models import DealershipInventory, DealershipPromotion, PrioritySuppliers


class DealershipInventoryFilter(CarFieldsFilterMixin, django_filters.FilterSet):
    car_model_path = "car_model"

    sale_price_min = django_filters.NumberFilter(field_name="sale_price", lookup_expr="gte")
    sale_price_max = django_filters.NumberFilter(field_name="sale_price", lookup_expr="lte")

    base_price_min = django_filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    base_price_max = django_filters.NumberFilter(field_name="base_price", lookup_expr="lte")

    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    low_stock = django_filters.BooleanFilter(method="filter_low_stock")
    quantity_min = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")

    dealership = django_filters.NumberFilter(field_name="dealership_id")

    class Meta:
        model = DealershipInventory
        fields: list[str] = []

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity=0)

    def filter_low_stock(self, queryset, name, value):
        return queryset.filter(quantity__lte=3) if value else queryset


class DealershipPromotionFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=DealershipPromotion.Status.choices)
    name = django_filters.CharFilter(lookup_expr="icontains")
    start_date_from = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    end_date_to = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")

    active_now = django_filters.BooleanFilter(method="filter_active_now")

    dealership = django_filters.NumberFilter(field_name="dealership_id")

    class Meta:
        model = DealershipPromotion
        fields: list[str] = []

    def filter_active_now(self, queryset, name, value):
        from django.utils import timezone

        today = timezone.now().date()
        active = queryset.filter(
            status=DealershipPromotion.Status.ACTIVE,
            start_date__lte=today,
            end_date__gte=today,
        )
        return active if value else queryset.exclude(id__in=active.values("id"))


class PrioritySuppliersFilter(django_filters.FilterSet):
    supplier = django_filters.NumberFilter(field_name="supplier_id")
    supplier_name = django_filters.CharFilter(field_name="supplier__name", lookup_expr="icontains")
    supplier_country = django_filters.CharFilter(field_name="supplier__country", lookup_expr="iexact")
    has_recent_deal = django_filters.BooleanFilter(method="filter_has_recent_deal")

    class Meta:
        model = PrioritySuppliers
        fields: list[str] = []

    def filter_has_recent_deal(self, queryset, name, value):
        if value:
            return queryset.filter(last_deal_at__isnull=False)
        return queryset.filter(last_deal_at__isnull=True)
