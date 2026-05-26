import os

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.http import urlsafe_base64_decode

from buyers.models import BuyerProfile
from core.services import AuthService, BaseOrganizationService, RegistrationService
from dealership.models import Dealership, WorkerProfileDealership
from invitations.models import Invitation
from rest_framework.exceptions import NotFound, ValidationError
from suppliers.services import SupplierService

from users.models import User
from users.utils import generate_confirmation_data


class BuyerService(RegistrationService):
    @classmethod
    @transaction.atomic
    def register_buyer(cls, data: dict):
        data = data.copy()

        password = data.pop("password")
        data.pop("password2")
        email = data.pop("email")

        user = cls.create_user(email=email, password=password, role=User.Role.BUYER[0])
        BuyerProfile.objects.create(user=user, is_active=False, **data)
        EmailService.send_confirmation_email(user)

        return user

    @classmethod
    def activate(cls, user):
        user.is_active = True
        user.is_email_verified = True

        user.save(
            update_fields=[
                "is_active",
                "is_email_verified",
            ]
        )

        profile = user.buyer_profile
        profile.is_active = True
        profile.save(update_fields=["is_active"])


class OrganizationServiceResolver:
    @staticmethod
    def resolve_by_invitation(invitation):
        if invitation.supplier:
            return SupplierService
        if invitation.dealership:
            return DealershipService
        raise ValueError("Organization service not found")


class DealershipService(BaseOrganizationService):
    organization_model = Dealership
    profile_model = WorkerProfileDealership
    organization_field = "dealership"
    profile_accessor = "worker_dealership"

    @classmethod
    def get_user_role(cls):
        return User.Role.WORKER_DEALERSHIP


class EmailService:
    SERVICES = {
        User.Role.BUYER: BuyerService,
        User.Role.WORKER_SUPPLIER: SupplierService,
        User.Role.WORKER_DEALERSHIP: DealershipService,
    }

    @staticmethod
    def send_confirmation_email(user):
        uid, token = generate_confirmation_data(user)

        confirm_url = f"http://{os.getenv('HOST')}/api/auth/confirm-email/{uid}/{token}/"

        send_mail(
            subject="Confirm your email",
            message=f"Click here to confirm:{confirm_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    @staticmethod
    def send_password_reset_email(user):
        uid, token = generate_confirmation_data(user)

        reset_url = f"http://{os.getenv('HOST')}/reset-password/{uid}/{token}/"

        send_mail(
            subject="Reset password",
            message=f"Click here to reset password:{reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    @staticmethod
    def confirm_email(uid: str, token: str) -> dict:
        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except Exception as e:
            raise NotFound("User not found") from e

        if not default_token_generator.check_token(user, token):
            raise ValidationError("Invalid or expired token")

        service = EmailService.SERVICES.get(user.role)

        if not service:
            raise ValidationError("Unsupported role")

        service.activate(user)

        refresh_token = AuthService.create_tokens(user)

        return {
            "message": "Email confirmed",
            "access": str(refresh_token.access_token),
            "refresh": str(refresh_token),
        }

    @staticmethod
    def send_invitation_email(invitation: Invitation):
        url = f"http://{os.getenv('HOST')}/register?token={invitation.token}/"

        send_mail(
            subject="You are invited",
            message=f"Click here to add to platform:{url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
        )


class PasswordResetService:
    @staticmethod
    def request_password_reset(email: str):
        user = User.objects.filter(email=email).first()
        if not user:
            return

        EmailService.send_password_reset_email(user)

    @staticmethod
    def reset_password(*, uid: str, token: str, password: str):
        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except Exception as e:
            raise NotFound("User not found") from e

        if not default_token_generator.check_token(user, token):
            raise ValidationError("Invalid or expired token")
        user.set_password(password)
        user.save(update_fields=["password"])
