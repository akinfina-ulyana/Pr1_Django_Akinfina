"""
The scoping logic—restricting access to "own" suppliers—resides within `get_queryset()`.
This means that a worker belonging to a different supplier will automatically receive a
404 error when attempting to access records owned by others via `get_object()`,
without the need for explicit checks in every method.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from users.permissions import IsAdminOrSupplierWorker

from suppliers.filters import (
    SupplierFilter,
    SupplierInventoryFilter,
    SupplierPromotionFilter,
    SupplierPromotionItemFilter,
)
from suppliers.models import (
    Supplier,
    SupplierInventory,
    SupplierPromotion,
    SupplierPromotionItem,
)
from suppliers.serializers import (
    SupplierInventorySerializer,
    SupplierPromotionItemSerializer,
    SupplierPromotionSerializer,
    SupplierSerializer,
)
from suppliers.services import SupplierService


class SupplierScopedMixin:
    supplier_lookup: str = "supplier"

    def _role(self):
        return self.request.auth.get("role") if self.request.auth else None

    def _own_supplier(self):
        return SupplierService.get_worker_supplier(self.request.user)

    def _scope(self, qs):
        if self._role() == "WORKER_SUPPLIER":
            supplier = self._own_supplier()
            if supplier is None:
                return qs.none()
            return qs.filter(**{self.supplier_lookup: supplier})
        return qs


class SupplierViewSet(
    SupplierScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SupplierSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SupplierFilter
    search_fields = ["name", "country", "city"]
    ordering_fields = ["name", "founded_year", "created_at"]
    ordering = ["-created_at"]
    supplier_lookup = "id"

    def get_queryset(self):
        return self._scope(Supplier.objects.filter(is_active=True))

    def get_permissions(self):
        return [IsAdminOrSupplierWorker()]

    def perform_update(self, serializer):
        SupplierService.update_supplier(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        if self._role() != "ADMIN":
            return Response({"detail": "Only admin can delete supplier"}, status=403)
        instance = self.get_object()
        SupplierService.soft_delete_supplier(instance)
        return Response({"detail": "Supplier soft deleted"}, status=status.HTTP_200_OK)


class SupplierInventoryViewSet(
    SupplierScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SupplierInventorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SupplierInventoryFilter
    search_fields = ["car_model__brand", "car_model__model_name"]
    ordering_fields = ["base_price", "quantity", "created_at"]
    ordering = ["-created_at"]
    supplier_lookup = "supplier"

    def get_queryset(self):
        qs = SupplierInventory.objects.filter(is_active=True).select_related("car_model", "supplier")
        return self._scope(qs)

    def get_permissions(self):
        return [IsAdminOrSupplierWorker()]

    def perform_create(self, serializer):
        supplier = self._own_supplier()
        if supplier is None:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("No supplier associated with this user")
        SupplierService.inventory_create(supplier=supplier, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        SupplierService.inventory_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        SupplierService.inventory_soft_delete(instance)
        return Response(
            {"detail": "SupplierInventory soft deleted"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="add-stock")
    def add_stock(self, request, pk=None):
        """POST /supplier-inventory/{id}/add-stock/  body: {"amount": 5}"""
        instance = self.get_object()
        amount = self._parse_amount(request.data.get("amount"))
        instance = SupplierService.inventory_add_stock(instance, amount)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], url_path="remove-stock")
    def remove_stock(self, request, pk=None):
        """POST /supplier-inventory/{id}/remove-stock/  body: {"amount": 2}"""
        instance = self.get_object()
        amount = self._parse_amount(request.data.get("amount"))
        instance = SupplierService.inventory_remove_stock(instance, amount)
        return Response(self.get_serializer(instance).data)

    @staticmethod
    def _parse_amount(raw):
        from rest_framework.exceptions import ValidationError

        try:
            return int(raw)
        except (TypeError, ValueError) as err:
            raise ValidationError({"amount": "Must be an integer"}) from err


class SupplierPromotionViewSet(
    SupplierScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SupplierPromotionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SupplierPromotionFilter
    search_fields = ["name", "description"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["-created_at"]
    supplier_lookup = "supplier"

    def get_queryset(self):
        qs = SupplierPromotion.objects.filter(is_active=True).select_related("supplier").prefetch_related("items")
        return self._scope(qs)

    def get_permissions(self):
        return [IsAdminOrSupplierWorker()]

    def perform_create(self, serializer):
        supplier = self._own_supplier()
        if supplier is None:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("No supplier associated with this user")
        SupplierService.promotion_create(supplier=supplier, validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        SupplierService.promotion_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        SupplierService.promotion_soft_delete(instance)
        return Response(
            {"detail": "SupplierPromotion soft deleted"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        instance = self.get_object()
        instance = SupplierService.promotion_activate(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        instance = SupplierService.promotion_cancel(instance)
        return Response(self.get_serializer(instance).data)


class SupplierPromotionItemViewSet(
    SupplierScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SupplierPromotionItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SupplierPromotionItemFilter
    ordering = ["-created_at"]
    supplier_lookup = "supplier_promotion__supplier"

    def get_queryset(self):
        qs = SupplierPromotionItem.objects.filter(is_active=True).select_related(
            "supplier_promotion",
            "supplier_promotion__supplier",
            "supplier_inventory",
        )
        return self._scope(qs)

    def get_permissions(self):
        return [IsAdminOrSupplierWorker()]

    def perform_create(self, serializer):
        promotion = serializer.validated_data["supplier_promotion"]
        if self._role() == "WORKER_SUPPLIER":
            SupplierService.assert_worker_owns_supplier(self.request.user, promotion.supplier)
        SupplierService.promotion_item_create(validated_data=serializer.validated_data)

    def perform_update(self, serializer):
        SupplierService.promotion_item_update(serializer.instance, serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        SupplierService.promotion_item_soft_delete(instance)
        return Response(
            {"detail": "SupplierPromotionItem soft deleted"},
            status=status.HTTP_200_OK,
        )
