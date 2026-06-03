import django_filters

from suppliers.models import Supplier, SupplierInventory, SupplierPromotion, SupplierPromotionItem


class SupplierFilter(django_filters.FilterSet):
    """
    SupplierFilter — used in SupplierViewSet.
    Used by: platform admin (sees all suppliers)
    """

    name = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="iexact")
    city = django_filters.CharFilter(lookup_expr="iexact")
    founded_year_min = django_filters.NumberFilter(field_name="founded_year", lookup_expr="gte")
    founded_year_max = django_filters.NumberFilter(field_name="founded_year", lookup_expr="lte")

    class Meta:
        model = Supplier
        fields: list[str] = []


class SupplierInventoryFilter(django_filters.FilterSet):
    """
    SupplierInventoryFilter is the main filter for the supplier worker.
    Contains:
    - all vehicle characteristics (via mixin);
    - parameters of the warehouse item itself (price, currency, availability, quantity).
    Does NOT contain filters by Supplier fields (country, name) - these are not needed
    for a single supplier worker.
    """

    car_model_path = "car_model"

    price_min = django_filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="base_price", lookup_expr="lte")
    currency = django_filters.MultipleChoiceFilter(choices=SupplierInventory.Currency.choices)
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    low_stock = django_filters.BooleanFilter(method="filter_low_stock")
    quantity_min = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")

    supplier = django_filters.NumberFilter(field_name="supplier_id")

    class Meta:
        model = SupplierInventory
        fields: list[str] = []

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity=0)

    def filter_low_stock(self, queryset, name, value):
        return queryset.filter(quantity__lte=3) if value else queryset


class SupplierPromotionFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=SupplierPromotion.Status.choices)
    name = django_filters.CharFilter(lookup_expr="icontains")
    start_date_from = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    end_date_to = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")

    supplier = django_filters.NumberFilter(field_name="supplier_id")

    class Meta:
        model = SupplierPromotion
        fields: list[str] = []


class SupplierPromotionItemFilter(django_filters.FilterSet):
    supplier_promotion = django_filters.NumberFilter(field_name="supplier_promotion_id")
    supplier_inventory = django_filters.NumberFilter(field_name="supplier_inventory_id")
    discount_min = django_filters.NumberFilter(field_name="discount_percent", lookup_expr="gte")
    discount_max = django_filters.NumberFilter(field_name="discount_percent", lookup_expr="lte")

    class Meta:
        model = SupplierPromotionItem
        fields: list[str] = []
