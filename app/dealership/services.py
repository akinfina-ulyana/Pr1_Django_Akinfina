from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from core.services import BaseOrganizationService
from rest_framework.exceptions import PermissionDenied, ValidationError

from dealership.models import (
    Dealership,
    DealershipInventory,
    DealershipPreferredCar,
    DealershipPromotion,
    DealershipPromotionItem,
    PrioritySuppliers,
    WorkerProfileDealership,
)


User = get_user_model()


class DealershipService(BaseOrganizationService):
    organization_model = Dealership
    profile_model = WorkerProfileDealership
    organization_field = "dealership"
    profile_accessor = "worker_dealership"

    @classmethod
    def get_user_role(cls):
        return User.Role.WORKER_DEALERSHIP

    @staticmethod
    def get_worker_dealership(user) -> Dealership | None:
        worker: WorkerProfileDealership | None = getattr(user, "worker_dealership", None)
        return worker.dealership if worker else None

    @staticmethod
    def assert_worker_owns_dealership(user, dealership: Dealership) -> None:
        own = DealershipService.get_worker_dealership(user)
        if own is None or own.id != dealership.id:
            raise PermissionDenied("Worker does not belong to this dealership")

    @staticmethod
    def update_dealership(dealership: Dealership, validated_data: dict) -> Dealership:
        for attr, value in validated_data.items():
            setattr(dealership, attr, value)
        dealership.save()
        return dealership

    @staticmethod
    def soft_delete_dealership(dealership: Dealership) -> None:
        dealership.is_active = False
        dealership.save(update_fields=["is_active"])

    @staticmethod
    @transaction.atomic
    def balance_deposit(dealership: Dealership, amount: Decimal) -> Dealership:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        Dealership.objects.filter(pk=dealership.pk).update(balance=F("balance") + amount)

        dealership.refresh_from_db(fields=["balance"])
        return dealership

    @staticmethod
    @transaction.atomic
    def balance_withdraw(
        dealership: Dealership,
        amount: Decimal,
    ) -> Dealership:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        dealership = Dealership.objects.select_for_update().get(pk=dealership.pk)

        if dealership.balance < amount:
            raise ValidationError({"amount": "Insufficient funds"})

        dealership.balance = F("balance") - amount
        dealership.save(update_fields=["balance"])

        dealership.refresh_from_db(fields=["balance"])
        return dealership

    @staticmethod
    def inventory_create(*, dealership: Dealership, validated_data: dict) -> DealershipInventory:
        return DealershipInventory.objects.create(dealership=dealership, **validated_data)

    @staticmethod
    def inventory_update(inventory: DealershipInventory, validated_data: dict) -> DealershipInventory:
        for attr, value in validated_data.items():
            setattr(inventory, attr, value)
        inventory.save()
        return inventory

    @staticmethod
    def inventory_soft_delete(inventory: DealershipInventory) -> None:
        inventory.is_active = False
        inventory.save(update_fields=["is_active"])

    @staticmethod
    def inventory_add_stock(inventory: DealershipInventory, amount: int) -> DealershipInventory:
        if amount <= 0:
            raise ValidationError({"amount": "Must be a positive integer"})
        DealershipInventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") + amount)
        inventory.refresh_from_db(fields=["quantity"])
        return inventory

    @staticmethod
    def inventory_remove_stock(inventory: DealershipInventory, amount: int) -> DealershipInventory:
        if amount <= 0:
            raise ValidationError({"amount": "Must be a positive integer"})
        if inventory.quantity < amount:
            raise ValidationError({"amount": "Not enough stock"})
        DealershipInventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") - amount)
        inventory.refresh_from_db(fields=["quantity"])
        return inventory

    @staticmethod
    def promotion_create(*, dealership: Dealership, validated_data: dict) -> DealershipPromotion:
        return DealershipPromotion.objects.create(dealership=dealership, **validated_data)

    @staticmethod
    def promotion_update(promotion: DealershipPromotion, validated_data: dict) -> DealershipPromotion:
        for attr, value in validated_data.items():
            setattr(promotion, attr, value)
        promotion.save()
        return promotion

    @staticmethod
    def promotion_soft_delete(promotion: DealershipPromotion) -> None:
        promotion.is_active = False
        promotion.save(update_fields=["is_active"])

    @staticmethod
    def promotion_activate(promotion: DealershipPromotion) -> DealershipPromotion:
        if promotion.status != DealershipPromotion.Status.DRAFT:
            raise ValidationError({"status": f"Can activate only from DRAFT, current is {promotion.status}"})
        promotion.status = DealershipPromotion.Status.ACTIVE
        promotion.save(update_fields=["status"])
        return promotion

    @staticmethod
    def promotion_cancel(promotion: DealershipPromotion) -> DealershipPromotion:
        if promotion.status in (
            DealershipPromotion.Status.EXPIRED,
            DealershipPromotion.Status.CANCELED,
        ):
            raise ValidationError({"status": f"Cannot cancel from status {promotion.status}"})
        promotion.status = DealershipPromotion.Status.CANCELED
        promotion.save(update_fields=["status"])
        return promotion

    @staticmethod
    def promotion_item_create(*, validated_data: dict) -> DealershipPromotionItem:
        promotion: DealershipPromotion = validated_data["dealership_promotion"]
        inventory: DealershipInventory = validated_data["dealership_inventory"]
        if promotion.dealership_id != inventory.dealership_id:
            raise ValidationError(
                {"dealership_inventory": "Inventory must belong to the same dealership as the promotion"}
            )
        return DealershipPromotionItem.objects.create(**validated_data)

    @staticmethod
    def promotion_item_update(item: DealershipPromotionItem, validated_data: dict) -> DealershipPromotionItem:
        for attr, value in validated_data.items():
            setattr(item, attr, value)
        item.save()
        return item

    @staticmethod
    def promotion_item_soft_delete(item: DealershipPromotionItem) -> None:
        item.is_active = False
        item.save(update_fields=["is_active"])

    @staticmethod
    def priority_supplier_create(*, dealership: Dealership, validated_data: dict) -> PrioritySuppliers:
        return PrioritySuppliers.objects.create(dealership=dealership, **validated_data)

    @staticmethod
    def priority_supplier_update(link: PrioritySuppliers, validated_data: dict) -> PrioritySuppliers:
        validated_data.pop("supplier", None)
        for attr, value in validated_data.items():
            setattr(link, attr, value)
        link.save()
        return link

    @staticmethod
    def priority_supplier_soft_delete(link: PrioritySuppliers) -> None:
        link.is_active = False
        link.save(update_fields=["is_active"])

    @staticmethod
    def preferred_car_create(*, dealership: Dealership, validated_data: dict) -> DealershipPreferredCar:
        return DealershipPreferredCar.objects.create(dealership=dealership, **validated_data)

    @staticmethod
    def preferred_car_update(pref: DealershipPreferredCar, validated_data: dict) -> DealershipPreferredCar:
        validated_data.pop("car_model", None)
        for attr, value in validated_data.items():
            setattr(pref, attr, value)
        pref.save()
        return pref

    @staticmethod
    def preferred_car_soft_delete(pref: DealershipPreferredCar) -> None:
        pref.is_active = False
        pref.save(update_fields=["is_active"])
