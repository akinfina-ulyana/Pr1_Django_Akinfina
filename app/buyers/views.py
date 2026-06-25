from decimal import Decimal
from urllib.request import Request

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import IsAdmin, IsAdminOrBuyer, IsBuyer

from buyers.filters import MarketplaceInventoryFilter
from buyers.models import BuyerProfile
from buyers.serializers import (
    BalanceOperationSerializer,
    BuyerProfileSerializer,
    MarketplaceInventorySerializer,
    OfferCreateSerializer,
    OfferReadSerializer,
)
from buyers.services import BuyerService, MarketplaceService, OfferService


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
    def deposit(self, request: Request) -> Response:
        # POST /buyers/me/deposit/  body: {"amount": "100.00"}

        profile = self._get_own_profile()
        serializer = BalanceOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount: Decimal = serializer.validated_data["amount"]
        profile = BuyerService.deposit(profile, amount)
        return Response({"balance": str(profile.balance)})

    @action(detail=False, methods=["post"], url_path="me/withdraw")
    def withdraw(self, request: Request) -> Response:
        # POST /buyers/me/withdraw/  body: {"amount": "50.00"}
        profile = self._get_own_profile()
        serializer = BalanceOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount: Decimal = serializer.validated_data["amount"]
        profile = BuyerService.withdraw(profile, amount)
        return Response({"balance": str(profile.balance)})


class DealershipMarketplaceViewSetForBuyers(viewsets.ReadOnlyModelViewSet):
    serializer_class = MarketplaceInventorySerializer
    permission_classes = [IsAdminOrBuyer]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MarketplaceInventoryFilter

    def get_queryset(self):
        return MarketplaceService.get_sellable_inventory()


class OfferCreateView(APIView):
    permission_classes = [IsBuyer]

    def post(self, request):
        serializer = OfferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = BuyerService.get_profile_for_user(request.user)
        if profile is None or not profile.is_active:
            return Response(
                {"detail": "Buyer profile not found or inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = OfferService.create_offer(
            buyer=profile,
            dealership_inventory_id=serializer.validated_data["dealership_inventory_id"],
        )

        return Response(OfferReadSerializer(offer).data, status=status.HTTP_201_CREATED)
