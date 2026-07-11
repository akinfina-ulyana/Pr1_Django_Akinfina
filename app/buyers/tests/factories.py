from decimal import Decimal

import factory
from dealership.tests.factories import DealershipFactory, DealershipInventoryFactory
from users.tests.factories import UserFactory

from buyers.models import BuyerProfile, Offer


class BuyerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BuyerProfile

    user = factory.SubFactory(UserFactory, role="BUYER")
    first_name = "Una"
    last_name = "Akinfina"
    balance = Decimal("0")
    is_active = True


class OfferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Offer

    buyer = factory.SubFactory(BuyerProfileFactory)
    dealership = factory.SubFactory(DealershipFactory)
    dealership_inventory = factory.SubFactory(DealershipInventoryFactory)
    final_price = Decimal("10000.00")
    status = Offer.Status.CREATED
    is_active = True
