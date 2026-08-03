from suppliers.tests.factories import SupplierFactory, SupplierInventoryFactory


class TestSupplierViewSetPermissions:
    """permission_classes = [IsAdminOrSupplierWorker]"""

    def test_anonymous_gets_401(self, api_client):
        r = api_client.get("/api/v1/suppliers/")
        assert r.status_code == 401

    def test_buyer_gets_403(self, buyer_client):
        r = buyer_client.get("/api/v1/suppliers/")
        assert r.status_code == 403

    def test_admin_sees_all_suppliers(self, admin_client, db):
        SupplierFactory.create_batch(3)
        r = admin_client.get("/api/v1/suppliers/")
        assert r.status_code == 200
        assert len(r.data) == 3


class TestSupplierViewSetScoping:
    def test_worker_sees_only_own_supplier(self, supplier_worker_client, db):
        SupplierFactory.create_batch(2)
        r = supplier_worker_client.get("/api/v1/suppliers/")
        assert r.status_code == 200
        assert len(r.data) == 1
        assert r.data[0]["id"] == supplier_worker_client.supplier.id

    def test_worker_without_profile_sees_empty(self, supplier_client, db):
        SupplierFactory.create_batch(2)
        r = supplier_client.get("/api/v1/suppliers/")
        assert r.status_code == 200
        assert len(r.data) == 0


class TestSupplierInventoryScoping:
    def test_worker_sees_only_own_inventory(self, supplier_worker_client, db):
        SupplierInventoryFactory(supplier=supplier_worker_client.supplier)
        SupplierInventoryFactory()
        r = supplier_worker_client.get("/api/v1/suppliers/supplier-inventory/")
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_admin_sees_all_inventory(self, admin_client, db):
        SupplierInventoryFactory.create_batch(3)
        r = admin_client.get("/api/v1/suppliers/supplier-inventory/")
        assert r.status_code == 200
        assert len(r.data) == 3
