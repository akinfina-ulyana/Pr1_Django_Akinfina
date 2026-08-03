from dealership.tests.factories import DealershipFactory


class TestDealershipViewSetPermissions:
    def test_anonymous_gets_401(self, api_client):
        r = api_client.get("/api/v1/dealership/")
        assert r.status_code == 401

    def test_buyer_gets_403(self, buyer_client):
        r = buyer_client.get("/api/v1/dealership/")
        assert r.status_code == 403

    def test_admin_sees_all_dealerships(self, admin_client, db):
        DealershipFactory.create_batch(3)
        r = admin_client.get("/api/v1/dealership/")
        assert r.status_code == 200
        assert len(r.data) == 3


class TestDealershipViewSetScoping:
    def test_worker_sees_only_own_dealership(self, dealership_worker_client, db):
        DealershipFactory.create_batch(2)
        r = dealership_worker_client.get("/api/v1/dealership/")
        assert r.status_code == 200
        assert len(r.data) == 1
        assert r.data[0]["id"] == dealership_worker_client.dealership.id

    def test_worker_without_profile_sees_empty(self, dealership_client, db):
        DealershipFactory.create_batch(2)
        r = dealership_client.get("/api/v1/dealership/")
        assert r.status_code == 200
        assert len(r.data) == 0
