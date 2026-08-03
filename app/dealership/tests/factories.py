import factory
from cars.tests.factories import CarModelFactory
from users.tests.factories import UserFactory

from dealership.models import Dealership, DealershipInventory, WorkerProfileDealership


class DealershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dealership

    name = factory.Sequence(lambda n: f"Dealership {n}")
    country = "RU"
    is_active = True


class DealershipInventoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DealershipInventory

    dealership = factory.SubFactory(DealershipFactory)
    car_model = factory.SubFactory(CarModelFactory)
    quantity = 1
    base_price = "15000.00"
    sale_price = "18000.00"
    is_active = True


class WorkerProfileDealershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkerProfileDealership

    user = factory.SubFactory(UserFactory, role="WORKER_DEALERSHIP")
    dealership = factory.SubFactory(DealershipFactory)
    first_name = "John"
    last_name = "Doe"
    phone = "+22222222222"
    position = WorkerProfileDealership.Position.MANAGER
    is_active = True
