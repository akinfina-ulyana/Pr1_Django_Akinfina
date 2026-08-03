class TestBuyerProfileMe:
    def test_buyer_sees_own_profile(self, buyer_with_profile):
        result = buyer_with_profile.get("/api/v1/buyers/me/")
        assert result.status_code == 200
        assert result.data["id"] == buyer_with_profile.profile.id

    def test_anonymous_gets_401(self, api_client):
        result = api_client.get("/api/v1/buyers/me/")
        assert result.status_code == 401

    def test_supplier_gets_403(self, supplier_client):
        r = supplier_client.get("/api/v1/buyers/me/")
        assert r.status_code == 403

    def test_buyer_without_profile_gets_404(self, buyer_client):
        r = buyer_client.get("/api/v1/buyers/me/")
        assert r.status_code == 404


class TestBuyerDeposit:
    def test_deposit_success(self, buyer_with_profile):
        r = buyer_with_profile.post(
            "/api/v1/buyers/me/deposit/",
            data={"amount": "500.00"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["balance"] == "500.00"

    def test_deposit_zero_rejected(self, buyer_with_profile):
        r = buyer_with_profile.post(
            "/api/v1/buyers/me/deposit/",
            data={"amount": "0.00"},
            format="json",
        )
        assert r.status_code == 400

    def test_deposit_unauthenticated(self, api_client):
        r = api_client.post(
            "/api/v1/buyers/me/deposit/",
            data={"amount": "100.00"},
            format="json",
        )
        assert r.status_code == 401


class TestBuyerWithdraw:
    def test_withdraw_success(self, buyer_with_profile):
        buyer_with_profile.post(
            "/api/v1/buyers/me/deposit/",
            data={"amount": "1000.00"},
            format="json",
        )
        r = buyer_with_profile.post(
            "/api/v1/buyers/me/withdraw/",
            data={"amount": "300.00"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["balance"] == "700.00"

    def test_withdraw_insufficient_funds(self, buyer_with_profile):
        r = buyer_with_profile.post(
            "/api/v1/buyers/me/withdraw/",
            data={"amount": "999.00"},
            format="json",
        )
        assert r.status_code == 400
