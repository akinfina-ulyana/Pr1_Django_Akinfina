from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from users.permissions import IsAdminOrIsDealershipWorker

from dealership.filters import (
    DealershipInventoryFilter,
    DealershipPromotionFilter,
    PrioritySuppliersFilter,
)
from dealership.models import (
    Dealership,
    DealershipInventory,
    DealershipPreferredCar,
    DealershipPromotion,
    DealershipPromotionItem,
    PrioritySuppliers,
)
from dealership.serializers import (
    BalanceOperationSerializer,
    DealershipInventorySerializer,
    DealershipPreferredCarSerializer,
    DealershipPromotionItemSerializer,
    DealershipPromotionSerializer,
    DealershipSerializer,
    PrioritySuppliersSerializer,
)
from dealership.services import DealershipService


class DealershipScopedMixin:
    dealership_lookup: str = "dealership"

    def _role(self):
        return self.request.auth.get("role") if self.request.auth else None

    def _own_dealership(self):
        return DealershipService.get_worker_dealership(self.request.user)

    def _scope(self, qs):
        if self._role() == "WORKER_DEALERSHIP":
            dealership = self._own_dealership()
            if dealership is None:
                return qs.none()
            return qs.filter(**{self.dealership_lookup: dealership.pk})
        return qs


class DealershipViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DealershipSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "country"]
    ordering_fields = ["name", "balance", "created_at"]
    ordering = ["-created_at"]
    dealership_lookup = "id"

    def get_queryset(self):
        return self._scope(Dealership.objects.filter(is_active=True))

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_update(self, serializer):
        DealershipService.update_dealership(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        if self._role() != "ADMIN":
            return Response({"detail": "Only admin can delete dealership"}, status=403)
        instance = self.get_object()
        DealershipService.soft_delete_dealership(instance)
        return Response({"detail": "Dealership soft deleted"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="balance")
    def balance(self, request, pk=None):
        """GET /dealerships/{id}/balance/"""
        instance = self.get_object()
        return Response({"balance": str(instance.balance)})

    @action(detail=True, methods=["post"], url_path="deposit")
    def deposit(self, request, pk=None):
        """POST /dealerships/{id}/deposit/  body: {"amount": "1000.00"}"""
        instance = self.get_object()
        amount = self._parse_amount(request.data.get("amount"))
        instance = DealershipService.balance_deposit(instance, amount)
        return Response({"balance": str(instance.balance)})

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        """POST /dealerships/{id}/withdraw/  body: {"amount": "500.00"}"""
        instance = self.get_object()
        amount = self._parse_amount(request.data.get("amount"))
        instance = DealershipService.balance_withdraw(instance, amount)
        return Response({"balance": str(instance.balance)})

    @staticmethod
    def _parse_amount(raw) -> Decimal:
        serializer = BalanceOperationSerializer(data={"amount": raw})
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["amount"]


class DealershipInventoryViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DealershipInventorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DealershipInventoryFilter
    search_fields = ["car_model__brand", "car_model__model_name"]
    ordering_fields = ["sale_price", "base_price", "quantity", "created_at"]
    ordering = ["-created_at"]
    dealership_lookup = "dealership"

    def get_queryset(self):
        return self._scope(DealershipInventory.objects.filter(is_active=True).select_related("car_model", "dealership"))

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_create(self, serializer):
        dealership = self._own_dealership()
        if dealership is None:
            raise PermissionDenied("No dealership associated with this user")
        DealershipService.inventory_create(dealership=dealership, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        DealershipService.inventory_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        DealershipService.inventory_soft_delete(instance)
        return Response({"detail": "DealershipInventory soft deleted"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add-stock")
    def add_stock(self, request, pk=None):
        """POST /dealership-inventory/{id}/add-stock/  body: {"amount": 5}"""
        instance = self.get_object()
        amount = self._parse_int(request.data.get("amount"))
        instance = DealershipService.inventory_add_stock(instance, amount)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], url_path="remove-stock")
    def remove_stock(self, request, pk=None):
        """POST /dealership-inventory/{id}/remove-stock/  body: {"amount": 2}"""
        instance = self.get_object()
        amount = self._parse_int(request.data.get("amount"))
        instance = DealershipService.inventory_remove_stock(instance, amount)
        return Response(self.get_serializer(instance).data)

    @staticmethod
    def _parse_int(raw, field_name="amount") -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError) as err:
            raise ValidationError({field_name: "Must be an integer"}) from err

        if value <= 0:
            raise ValidationError({field_name: "Must be positive"})

        return value


class DealershipPromotionViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DealershipPromotionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DealershipPromotionFilter
    search_fields = ["name", "description"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["-created_at"]
    dealership_lookup = "dealership"

    def get_queryset(self):
        return self._scope(
            DealershipPromotion.objects.filter(is_active=True).select_related("dealership").prefetch_related("items")
        )

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_create(self, serializer):
        dealership = self._own_dealership()
        if dealership is None:
            raise PermissionDenied("No dealership associated with this user")
        DealershipService.promotion_create(dealership=dealership, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        DealershipService.promotion_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        DealershipService.promotion_soft_delete(instance)
        return Response({"detail": "DealershipPromotion soft deleted"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """POST /dealership-promotions/{id}/activate/ — DRAFT → ACTIVE"""
        instance = self.get_object()
        instance = DealershipService.promotion_activate(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """POST /dealership-promotions/{id}/cancel/ — → CANCELED"""
        instance = self.get_object()
        instance = DealershipService.promotion_cancel(instance)
        return Response(self.get_serializer(instance).data)


class DealershipPromotionItemViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DealershipPromotionItemSerializer
    dealership_lookup = "dealership_promotion__dealership"

    def get_queryset(self):
        return self._scope(
            DealershipPromotionItem.objects.filter(is_active=True).select_related(
                "dealership_promotion",
                "dealership_promotion__dealership",
                "dealership_inventory",
            )
        )

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_create(self, serializer):
        promotion = serializer.validated_data["dealership_promotion"]
        if self._role() == "WORKER_DEALERSHIP":
            DealershipService.assert_worker_owns_dealership(self.request.user, promotion.dealership)
        DealershipService.promotion_item_create(validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        DealershipService.promotion_item_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        DealershipService.promotion_item_soft_delete(instance)
        return Response({"detail": "DealershipPromotionItem soft deleted"}, status=status.HTTP_200_OK)


class PrioritySuppliersViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PrioritySuppliersSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PrioritySuppliersFilter
    search_fields = ["supplier__name", "note"]
    ordering_fields = ["created_at", "last_deal_at"]
    ordering = ["-created_at"]
    dealership_lookup = "dealership"

    def get_queryset(self):
        return self._scope(PrioritySuppliers.objects.filter(is_active=True).select_related("supplier", "dealership"))

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_create(self, serializer):
        dealership = self._own_dealership()
        if dealership is None:
            raise PermissionDenied("No dealership associated with this user")
        DealershipService.priority_supplier_create(dealership=dealership, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        DealershipService.priority_supplier_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        DealershipService.priority_supplier_soft_delete(instance)
        return Response({"detail": "PrioritySupplier link soft deleted"}, status=status.HTTP_200_OK)


class DealershipPreferredCarViewSet(
    DealershipScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DealershipPreferredCarSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["car_model__brand", "car_model__model_name"]
    ordering_fields = ["created_at", "min_quantity"]
    ordering = ["-created_at"]
    dealership_lookup = "dealership"

    def get_queryset(self):
        return self._scope(
            DealershipPreferredCar.objects.filter(is_active=True).select_related("car_model", "dealership")
        )

    def get_permissions(self):
        return [IsAdminOrIsDealershipWorker()]

    def perform_create(self, serializer):
        dealership = self._own_dealership()
        if dealership is None:
            raise PermissionDenied("No dealership associated with this user")
        DealershipService.preferred_car_create(dealership=dealership, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        DealershipService.preferred_car_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        DealershipService.preferred_car_soft_delete(instance)
        return Response({"detail": "DealershipPreferredCar soft deleted"}, status=status.HTTP_200_OK)
