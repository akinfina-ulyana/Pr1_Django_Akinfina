from django.utils import timezone

from users.services import EmailService

from .models import Invitation


class InvitationService:
    @staticmethod
    def create_invitation(*, email, position, supplier=None, dealership=None, created_by=None):
        invitation = Invitation.objects.create(
            email=email, position=position, supplier=supplier, dealership=dealership, created_by=created_by
        )

        EmailService.send_invitation_email(invitation)

        return invitation

    @staticmethod
    def validate_token(token: str) -> Invitation:
        invitation = Invitation.objects.filter(token=token).first()

        if not invitation:
            raise ValueError("Invalid token")

        if invitation.status != Invitation.Status.PENDING:
            raise ValueError("Invitation already used")

        if invitation.expires_at < timezone.now():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save()
            raise ValueError("Invitation expired")

        return invitation
