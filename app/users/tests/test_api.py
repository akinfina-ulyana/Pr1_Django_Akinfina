from users.models import User
from users.tests.factories import UserFactory


class TestCustomTokenObtainPair:
    def test_login_success(self, api_client, db):
        UserFactory(email="login@test.test", password="Secret123!")

        response = api_client.post(
            "/api/v1/auth/login/",
            data={"email": "login@test.test", "password": "Secret123!"},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, db):
        UserFactory(email="login@test.test", password="Secret123!")

        response = api_client.post(
            "/api/v1/auth/login/",
            data={"email": "login@test.test", "password": "wrong"},
            format="json",
        )

        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, buyer_client):
        response = buyer_client.post(
            "/api/v1/auth/logout/",
            data={"refresh": buyer_client.refresh},
            format="json",
        )
        assert response.status_code == 205

    def test_logout_unauthenticated(self, api_client):
        response = api_client.post("/api/v1/auth/logout/", data={}, format="json")
        assert response.status_code == 401

    def test_logout_invalid_token(self, buyer_client):
        response = buyer_client.post(
            "/api/v1/auth/logout/",
            data={"refresh": "invalid.token.here"},
            format="json",
        )
        assert response.status_code == 400


class TestRegisterBuyer:
    def test_register_buyer_success(self, api_client, db):
        payload = {
            "email": "newbuyer@test.test",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
            "first_name": "Una",
            "last_name": "Aninta",
        }
        response = api_client.post(
            "/api/v1/auth/register/buyer/",
            data=payload,
            format="json",
        )
        assert response.status_code == 201
        assert User.objects.filter(email="newbuyer@test.test").exists()

    def test_register_buyer_password_mismatch(self, api_client, db):
        payload = {
            "email": "newbuyer@test.test",
            "password": "StrongPass123!",
            "password2": "DifferentPass123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = api_client.post(
            "/api/v1/auth/register/buyer/",
            data=payload,
            format="json",
        )
        assert response.status_code == 400
        assert not User.objects.filter(email="newbuyer@test.test").exists()
