from django.db.models import Q

import django_filters

from cars.models import CarModel


class CarFieldsFilterMixin(django_filters.FilterSet):
    """
    car_model_path is the path from the FilterSet model to the CarModel.
    For SupplierInventory, this is simply 'car_model'.
    """

    car_model_path: str = "car_model"

    brand = django_filters.CharFilter(method="_apply")
    model_name = django_filters.CharFilter(method="_apply")
    generation = django_filters.CharFilter(method="_apply")

    body_type = django_filters.MultipleChoiceFilter(choices=CarModel.BodyType.choices, method="_apply")
    fuel_type = django_filters.MultipleChoiceFilter(choices=CarModel.FuelType.choices, method="_apply")
    transmission = django_filters.MultipleChoiceFilter(choices=CarModel.Transmission.choices, method="_apply")
    drive_type = django_filters.MultipleChoiceFilter(choices=CarModel.DriveType.choices, method="_apply")

    engine_volume_min = django_filters.NumberFilter(method="_apply")
    engine_volume_max = django_filters.NumberFilter(method="_apply")
    horsepower_min = django_filters.NumberFilter(method="_apply")
    horsepower_max = django_filters.NumberFilter(method="_apply")
    seat_count = django_filters.NumberFilter(method="_apply")
    door_count = django_filters.NumberFilter(method="_apply")
    year = django_filters.NumberFilter(method="filter_by_year")

    _field_map = {
        "brand": ("brand", "iexact"),
        "model_name": ("model_name", "iexact"),
        "generation": ("generation", "icontains"),
        "body_type": ("body_type", "in"),
        "fuel_type": ("fuel_type", "in"),
        "transmission": ("transmission", "in"),
        "drive_type": ("drive_type", "in"),
        "engine_volume_min": ("engine_volume", "gte"),
        "engine_volume_max": ("engine_volume", "lte"),
        "horsepower_min": ("horsepower", "gte"),
        "horsepower_max": ("horsepower", "lte"),
        "seat_count": ("seat_count", "exact"),
        "door_count": ("door_count", "exact"),
    }

    def _apply(self, queryset, name, value):
        field, lookup = self._field_map[name]
        return queryset.filter(**{f"{self.car_model_path}__{field}__{lookup}": value})

    def filter_by_year(self, queryset, name, value):
        path = self.car_model_path
        return queryset.filter(
            (Q(**{f"{path}__production_year_from__lte": value}) | Q(**{f"{path}__production_year_from__isnull": True}))
            & (Q(**{f"{path}__production_year_to__gte": value}) | Q(**{f"{path}__production_year_to__isnull": True}))
        )
