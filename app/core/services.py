from abc import ABC, abstractmethod
from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models, transaction

from users.serializers import CustomTokenObtainPairSerializer


User = get_user_model()


class RegistrationService:
    @classmethod
    def create_user(cls, *, email: str, password: str, role: str):
        return User.objects.create_user(email=email, password=password, role=role, is_active=False)

    @classmethod
    def activate(cls, user):
        raise NotImplementedError


class BaseOrganizationService(RegistrationService, ABC):
    organization_model: type[models.Model]
    profile_model: type[models.Model]
    organization_field: ClassVar[str]
    profile_accessor: ClassVar[str]

    @classmethod
    @transaction.atomic
    def register(cls, data: dict):
        from users.services import EmailService

        data = data.copy()

        password = data.pop("password")
        data.pop("password2")
        email = data.pop("email")

        first_name = data.pop("first_name")
        last_name = data.pop("last_name")
        phone = data.pop("phone")
        country = data.pop("country", "")

        organization = cls.organization_model.objects.create(is_active=False, **data)

        user = cls.create_user(email=email, password=password, role=cls.get_user_role())

        profile_data = {
            "user": user,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "country": country,
            "position": cls.get_admin_position(),
            "is_active": False,
            cls.organization_field: organization,
        }

        cls.profile_model.objects.create(**profile_data)
        EmailService.send_confirmation_email(user=user)

        return user

    @classmethod
    @transaction.atomic
    def register_worker_by_invitation(cls, *, invitation, password, first_name, last_name, phone):
        user = User.objects.create_user(
            email=invitation.email, password=password, role=cls.get_user_role(), is_active=True, is_email_verified=True
        )

        organization = getattr(invitation, cls.organization_field)
        cls.profile_model.objects.create(
            user=user,
            **{
                cls.organization_field: organization,
                "position": invitation.position,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "is_active": True,
            },
        )
        invitation.status = invitation.Status.ACCEPTED
        invitation.save(update_fields=["status"])

        token = CustomTokenObtainPairSerializer.get_token(user)

        return {
            "user": user,
            "access": str(token.access_token),
            "refresh": str(token),
        }

    @classmethod
    @abstractmethod
    def get_user_role(cls):
        raise NotImplementedError

    @classmethod
    def get_admin_position(cls):
        return "ADMIN"

    @classmethod
    @transaction.atomic
    def activate(cls, user):
        user.is_active = True
        user.is_email_verified = True

        user.save(
            update_fields=[
                "is_active",
                "is_email_verified",
            ]
        )

        profile = getattr(user, cls.profile_accessor)

        profile.is_active = True
        profile.save(update_fields=["is_active"])

        organization = getattr(profile, cls.organization_field)

        organization.is_active = True

        organization.save(update_fields=["is_active"])
