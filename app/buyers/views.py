from decimal import Decimal

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from users.permissions import IsAdmin, IsAdminOrBuyer

from buyers.models import BuyerProfile
from buyers.serializers import (
    BalanceOperationSerializer,
    BuyerProfileSerializer,
)
from buyers.services import BuyerService


class BuyerProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = BuyerProfile.objects.select_related("user").all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "user__email"]
    ordering_fields = ["created_at", "balance", "last_name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"deposit", "withdraw"}:
            return BalanceOperationSerializer
        return BuyerProfileSerializer

    def get_permissions(self):
        admin_only_actions = {"list", "retrieve", "update", "partial_update", "destroy"}
        if self.action in admin_only_actions:
            return [IsAdmin()]
        return [IsAdminOrBuyer()]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.auth.get("role") if self.request.auth else None
        if role == "BUYER":
            return qs.filter(user=self.request.user)
        return qs

    def perform_update(self, serializer):
        BuyerService.update_profile(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        BuyerService.soft_delete_profile(instance)
        return Response(
            {"detail": "BuyerProfile soft deleted"},
            status=status.HTTP_200_OK,
        )

    def _get_own_profile(self) -> BuyerProfile:
        profile = BuyerService.get_profile_for_user(self.request.user)
        if profile is None:
            raise NotFound("Buyer profile not found for current user")
        return profile

    @action(detail=False, methods=["get", "patch", "delete"], url_path="me")
    def me(self, request):
        profile = self._get_own_profile()

        if request.method == "GET":
            return Response(self.get_serializer(profile).data)

        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            BuyerService.update_profile(profile, serializer.validated_data)
            return Response(self.get_serializer(profile).data)

        # DELETE
        BuyerService.soft_delete_profile(profile)
        return Response({"detail": "Profile deactivated"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="me/balance")
    def balance(self, request):
        # GET /buyers/me/balance/
        profile = self._get_own_profile()
        return Response({"balance": str(BuyerService.get_balance(profile))})

    @action(detail=False, methods=["post"], url_path="me/deposit")
    def deposit(self, request):
        # POST /buyers/me/deposit/  body: {"amount": "100.00"}

        profile = self._get_own_profile()
        serializer = BalanceOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount: Decimal = serializer.validated_data["amount"]
        profile = BuyerService.deposit(profile, amount)
        return Response({"balance": str(profile.balance)})

    @action(detail=False, methods=["post"], url_path="me/withdraw")
    def withdraw(self, request):
        # POST /buyers/me/withdraw/  body: {"amount": "50.00"}
        profile = self._get_own_profile()
        serializer = BalanceOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount: Decimal = serializer.validated_data["amount"]
        profile = BuyerService.withdraw(profile, amount)
        return Response({"balance": str(profile.balance)})
