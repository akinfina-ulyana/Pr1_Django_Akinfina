from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from core.services import BaseOrganizationService
from rest_framework.exceptions import PermissionDenied, ValidationError

from suppliers.models import (
    Supplier,
    SupplierInventory,
    SupplierPromotion,
    SupplierPromotionItem,
    WorkerProfileSupplier,
)


User = get_user_model()


class SupplierService(BaseOrganizationService):
    organization_model = Supplier
    profile_model = WorkerProfileSupplier
    organization_field = "supplier"
    profile_accessor = "worker_supplier"

    @classmethod
    def get_user_role(cls):
        return User.Role.WORKER_SUPPLIER

    @staticmethod
    def get_worker_supplier(user) -> Supplier | None:
        """
        Returns the provider organization to which the worker is bound.
        If the user doesn't have a profile, returns None.
        """
        worker: WorkerProfileSupplier | None = getattr(user, "worker_supplier", None)
        return worker.supplier if worker else None

    @staticmethod
    def assert_worker_owns_supplier(user, supplier: Supplier) -> None:
        """
        Checks that the worker belongs to this provider.
        Used in actions where queryset scoping isn't sufficient
        (for example, when creating an entity, get_object() won't work).
        """
        own = SupplierService.get_worker_supplier(user)
        if own is None or own.id != supplier.id:
            raise PermissionDenied("Worker does not belong to this supplier")

    @staticmethod
    def update_supplier(supplier: Supplier, validated_data: dict) -> Supplier:
        for attr, value in validated_data.items():
            setattr(supplier, attr, value)
        supplier.save()
        return supplier

    @staticmethod
    def soft_delete_supplier(supplier: Supplier) -> None:
        supplier.is_active = False
        supplier.save(update_fields=["is_active"])

    @staticmethod
    def inventory_create(*, supplier: Supplier, validated_data: dict) -> SupplierInventory:
        """
        Creates a record in the supplier's warehouse.
        """
        return SupplierInventory.objects.create(supplier=supplier, **validated_data)

    @staticmethod
    def inventory_update(inventory: SupplierInventory, validated_data: dict) -> SupplierInventory:
        for attr, value in validated_data.items():
            setattr(inventory, attr, value)
        inventory.save()
        return inventory

    @staticmethod
    def inventory_soft_delete(inventory: SupplierInventory) -> None:
        inventory.is_active = False
        inventory.save(update_fields=["is_active"])

    @staticmethod
    def inventory_add_stock(inventory: SupplierInventory, amount: int) -> SupplierInventory:
        """
        Atomic replenishment via F-expression.
        Safe for concurrent requests (two workers simultaneously doing +5 and +3).
        """
        if amount <= 0:
            raise ValidationError({"amount": "Must be a positive integer"})
        SupplierInventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") + amount)
        inventory.refresh_from_db(fields=["quantity"])
        return inventory

    @staticmethod
    def inventory_remove_stock(inventory: SupplierInventory, amount: int) -> SupplierInventory:
        """
        Write-off from warehouse.
        """
        if amount <= 0:
            raise ValidationError({"amount": "Must be a positive integer"})
        if inventory.quantity < amount:
            raise ValidationError({"amount": "Not enough stock"})
        SupplierInventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") - amount)
        inventory.refresh_from_db(fields=["quantity"])
        return inventory

    @staticmethod
    def promotion_create(*, supplier: Supplier, validated_data: dict) -> SupplierPromotion:
        return SupplierPromotion.objects.create(supplier=supplier, **validated_data)

    @staticmethod
    def promotion_update(promotion: SupplierPromotion, validated_data: dict) -> SupplierPromotion:
        for attr, value in validated_data.items():
            setattr(promotion, attr, value)
        promotion.save()
        return promotion

    @staticmethod
    def promotion_soft_delete(promotion: SupplierPromotion) -> None:
        promotion.is_active = False
        promotion.save(update_fields=["is_active"])

    @staticmethod
    def promotion_activate(promotion: SupplierPromotion) -> SupplierPromotion:
        """
        Transferring shares from DRAFT to ACTIVE.
        """
        if promotion.status != SupplierPromotion.Status.DRAFT:
            raise ValidationError({"status": f"Can activate only from DRAFT, current is {promotion.status}"})
        promotion.status = SupplierPromotion.Status.ACTIVE
        promotion.save(update_fields=["status"])
        return promotion

    @staticmethod
    def promotion_cancel(promotion: SupplierPromotion) -> SupplierPromotion:
        if promotion.status in (
            SupplierPromotion.Status.EXPIRED,
            SupplierPromotion.Status.CANCELED,
        ):
            raise ValidationError({"status": f"Cannot cancel from status {promotion.status}"})
        promotion.status = SupplierPromotion.Status.CANCELED
        promotion.save(update_fields=["status"])
        return promotion

    @staticmethod
    @transaction.atomic
    def promotion_item_create(*, validated_data: dict) -> SupplierPromotionItem:
        """
        Creates a discount on a specific warehouse item as part of a promotion.
        """
        promotion: SupplierPromotion = validated_data["supplier_promotion"]
        inventory: SupplierInventory = validated_data["supplier_inventory"]
        if promotion.supplier_id != inventory.supplier_id:
            raise ValidationError({"supplier_inventory": "Inventory must belong to the same supplier as the promotion"})
        return SupplierPromotionItem.objects.create(**validated_data)

    @staticmethod
    def promotion_item_update(item: SupplierPromotionItem, validated_data: dict) -> SupplierPromotionItem:
        for attr, value in validated_data.items():
            setattr(item, attr, value)
        item.save()
        return item

    @staticmethod
    def promotion_item_soft_delete(item: SupplierPromotionItem) -> None:
        item.is_active = False
        item.save(update_fields=["is_active"])
