from dealership.models import Dealership
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from suppliers.models import Supplier

from .serializers import InvitationCreateSerializer
from .services import InvitationService


class InvitationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        supplier = None
        dealership = None

        if data.get("supplier_id"):
            supplier = Supplier.objects.get(id=data["supplier_id"])

        if data.get("dealership_id"):
            dealership = Dealership.objects.get(id=data["dealership_id"])

        invitation = InvitationService.create_invitation(
            email=data["email"],
            position=data["position"],
            supplier=supplier,
            dealership=dealership,
            created_by=request.user,
        )

        return Response({"id": invitation.id})
