from datetime import timedelta
from decimal import Decimal  # noqa: F401

from django.utils import timezone

import factory
from suppliers.tests.factories import SupplierFactory
from users.tests.factories import UserFactory

from invitations.models import Invitation


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    email = factory.Sequence(lambda n: f"invited{n}@test.test")
    position = "MANAGER"
    created_by = factory.SubFactory(UserFactory, role="WORKER_SUPPLIER")
    supplier = factory.SubFactory(SupplierFactory)
    status = Invitation.Status.PENDING
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
