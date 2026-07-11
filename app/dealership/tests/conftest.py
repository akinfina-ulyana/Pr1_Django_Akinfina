import pytest
from conftest import create_auth_client

from dealership.tests.factories import WorkerProfileDealershipFactory


@pytest.fixture
def dealership_worker_client(db):
    profile = WorkerProfileDealershipFactory()
    client = create_auth_client(profile.user)
    client.dealership = profile.dealership
    return client
