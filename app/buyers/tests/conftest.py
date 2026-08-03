import pytest
from conftest import create_auth_client

from buyers.tests.factories import BuyerProfileFactory


@pytest.fixture
def buyer_with_profile(db):
    profile = BuyerProfileFactory()
    client = create_auth_client(profile.user)
    client.profile = profile
    return client
