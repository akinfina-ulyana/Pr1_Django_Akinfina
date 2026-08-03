import factory

from cars.models import CarModel


class CarModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CarModel

    brand = "Toyota"
    model_name = factory.Sequence(lambda n: f"Model_{n}")
    body_type = CarModel.BodyType.SEDAN
    fuel_type = CarModel.FuelType.PETROL
    is_active = True
    # we don't need other fields, will be default values
