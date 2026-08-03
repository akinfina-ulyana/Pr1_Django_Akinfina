import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User


#
@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(
        email="user@test.test",
        password="Test1234!",
        role=User.Role.BUYER,
        is_active=True,
        is_email_verified=True,
        **kwargs,
    ):
        return User.objects.create_user(
            email=email,
            password=password,
            role=role,
            is_active=is_active,
            is_email_verified=is_email_verified,
            **kwargs,
        )

    return _make


def create_auth_client(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    client.refresh = str(refresh)
    client.user = user
    return client


@pytest.fixture
def buyer_client(make_user):
    user = make_user(role=User.Role.BUYER)
    return create_auth_client(user)


@pytest.fixture
def supplier_client(make_user):
    user = make_user(role=User.Role.WORKER_SUPPLIER)
    return create_auth_client(user)


@pytest.fixture
def dealership_client(make_user):
    user = make_user(role=User.Role.WORKER_DEALERSHIP)
    return create_auth_client(user)


@pytest.fixture
def admin_client(make_user):
    user = make_user(role=User.Role.ADMIN)
    return create_auth_client(user)
