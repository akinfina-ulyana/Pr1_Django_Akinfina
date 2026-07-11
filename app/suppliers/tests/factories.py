import factory
from cars.tests.factories import CarModelFactory
from users.tests.factories import UserFactory

from suppliers.models import (
    Supplier,
    SupplierInventory,
    SupplierPromotion,
    WorkerProfileSupplier,
)


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier

    name = factory.Sequence(lambda n: f"Supplier {n}")
    country = "DE"
    city = "Berlin"
    address = "Berlin St 1"
    founded_year = 2000
    contact_email = factory.Sequence(lambda n: f"supplier{n}@test.test")
    is_active = True


class WorkerProfileSupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkerProfileSupplier

    user = factory.SubFactory(UserFactory, role="WORKER_SUPPLIER")
    supplier = factory.SubFactory(SupplierFactory)
    first_name = "Milano"
    last_name = "Italiano"
    phone = "+70000000000"
    position = WorkerProfileSupplier.Position.MANAGER
    is_active = True


class SupplierInventoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierInventory

    supplier = factory.SubFactory(SupplierFactory)
    car_model = factory.SubFactory(CarModelFactory)
    quantity = 10
    base_price = "15000.00"
    currency = SupplierInventory.Currency.USD
    is_active = True


class SupplierPromotionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierPromotion

    supplier = factory.SubFactory(SupplierFactory)
    name = factory.Sequence(lambda n: f"Promo {n}")
    start_date = "2026-01-01"
    end_date = "2025-12-31"
    status = SupplierPromotion.Status.DRAFT
    is_active = True
