from datetime import timedelta

from django.utils import timezone

import pytest

from invitations.services import InvitationService
from invitations.tests.factories import InvitationFactory


@pytest.mark.service
class TestInvitationServiceValidateToken:
    def test_valid_pending_token(self, db):
        invitation = InvitationFactory()
        result = InvitationService.validate_token(invitation.token)
        assert result.id == invitation.id

    def test_invalid_token_raises(self, db):
        with pytest.raises(ValueError, match="Invalid token"):
            InvitationService.validate_token("00000000-0000-0000-0000-000000000000")

    def test_already_used_raises(self, db):
        invitation = InvitationFactory(status="ACCEPTED")
        with pytest.raises(ValueError, match="already used"):
            InvitationService.validate_token(invitation.token)

    def test_expired_token_marks_and_raises(self, db):
        invitation = InvitationFactory(expires_at=timezone.now() - timedelta(days=1))
        with pytest.raises(ValueError, match="expired"):
            InvitationService.validate_token(invitation.token)

        invitation.refresh_from_db()
        assert invitation.status == "EXPIRED"
