import pytest
from conftest import create_auth_client
from suppliers.tests.factories import WorkerProfileSupplierFactory


@pytest.fixture
def supplier_worker_client(db):
    profile = WorkerProfileSupplierFactory()
    client = create_auth_client(profile.user)
    client.supplier = profile.supplier
    return client
