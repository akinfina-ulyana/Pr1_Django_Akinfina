class TestInvitationCreate:
    def test_supplier_worker_creates_invitation(self, supplier_worker_client, db, mocker):
        supplier = supplier_worker_client.supplier
        mock_send = mocker.patch("invitations.services.EmailService.send_invitation_email")

        r = supplier_worker_client.post(
            "/api/v1/invitations/",
            data={
                "email": "newworker@test.test",
                "position": "MANAGER",
                "supplier_id": supplier.id,
            },
            format="json",
        )
        assert r.status_code == 200
        assert "id" in r.data
        mock_send.assert_called_once()

    def test_anonymous_gets_401(self, api_client):
        r = api_client.post(
            "/api/v1/invitations/",
            data={"email": "x@t.test", "position": "MANAGER"},
            format="json",
        )
        assert r.status_code == 401

    def test_buyer_gets_403(self, buyer_client):
        r = buyer_client.post(
            "/api/v1/invitations/",
            data={"email": "x@t.test", "position": "MANAGER"},
            format="json",
        )
        assert r.status_code == 200
