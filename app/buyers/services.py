import logging
import os
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from dealership.models import (
    DealershipInventory,
    DealershipPromotion,
    DealershipPromotionItem,
)
from dealership.services import DealershipService
from rest_framework.exceptions import ValidationError

from buyers.models import BuyerProfile, Offer


logger = logging.getLogger(__name__)


class BuyerService:
    @staticmethod
    def get_profile_for_user(user) -> BuyerProfile | None:
        """Returns the buyer profile for the user, or None."""
        return getattr(user, "buyer_profile", None)

    @staticmethod
    def update_profile(profile: BuyerProfile, validated_data: dict) -> BuyerProfile:
        for attr, value in validated_data.items():
            setattr(profile, attr, value)
        profile.save()
        return profile

    @staticmethod
    def soft_delete_profile(profile: BuyerProfile) -> None:
        profile.is_active = False
        profile.save(update_fields=["is_active"])

    @staticmethod
    def deposit(profile: BuyerProfile, amount: Decimal) -> BuyerProfile:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        BuyerProfile.objects.filter(pk=profile.pk).update(balance=F("balance") + amount)
        profile.refresh_from_db(fields=["balance"])
        return profile

    @staticmethod
    @transaction.atomic
    def withdraw(profile: BuyerProfile, amount: Decimal) -> BuyerProfile:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        locked = BuyerProfile.objects.select_for_update().filter(pk=profile.pk).first()
        if locked is None:
            raise ValidationError({"detail": "Profile not found"})
        if locked.balance < amount:
            raise ValidationError({"amount": "Insufficient funds"})

        BuyerProfile.objects.filter(pk=profile.pk).update(balance=F("balance") - amount)
        profile.refresh_from_db(fields=["balance"])
        return profile

    @staticmethod
    def get_balance(profile: BuyerProfile) -> Decimal:
        return profile.balance


class MarketplaceService:
    @staticmethod
    def get_sellable_inventory():
        today = timezone.now().date()

        active_discount_subq = (
            DealershipPromotionItem.objects.filter(
                dealership_inventory=OuterRef("pk"),
                is_active=True,
                dealership_promotion__status=DealershipPromotion.Status.ACTIVE,
                dealership_promotion__is_active=True,
                dealership_promotion__start_date__lte=today,
                dealership_promotion__end_date__gte=today,
            )
            .order_by("-discount_percent")
            .values("discount_percent")[:1]
        )

        return (
            DealershipInventory.objects.filter(is_active=True, quantity__gt=0, dealership__is_active=True)
            .annotate(
                discount=Coalesce(
                    Subquery(active_discount_subq),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=5, decimal_places=2),
                )
            )
            .annotate(effective_price=F("sale_price") * (Decimal("1") - F("discount") / Decimal("100")))
            .select_related("dealership", "car_model")
            .order_by("effective_price")
        )


class OfferService:
    @staticmethod
    def effective_price_for(inventory: DealershipInventory) -> Decimal:
        today = timezone.now().date()

        active_discount_subq = (
            DealershipPromotionItem.objects.filter(
                dealership_inventory=OuterRef("pk"),
                is_active=True,
                dealership_promotion__status=DealershipPromotion.Status.ACTIVE,
                dealership_promotion__is_active=True,
                dealership_promotion__start_date__lte=today,
                dealership_promotion__end_date__gte=today,
            )
            .order_by("-discount_percent")
            .values("discount_percent")[:1]
        )

        row = (
            DealershipInventory.objects.filter(pk=inventory.pk)
            .annotate(
                discount=Coalesce(
                    Subquery(active_discount_subq),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=5, decimal_places=2),
                )
            )
            .annotate(effective_price=F("sale_price") * (Decimal("1") - F("discount") / Decimal("100")))
            .get()
        )
        return row.effective_price.quantize(Decimal("0.01"))

    @staticmethod
    @transaction.atomic
    def create_offer(*, buyer: BuyerProfile, dealership_inventory_id: int) -> Offer:
        try:
            inventory = DealershipInventory.objects.select_related("dealership", "car_model").get(
                pk=dealership_inventory_id
            )
        except DealershipInventory.DoesNotExist as error:
            raise ValidationError({"dealership_inventory_id": "Position not found"}) from error

        if not inventory.is_active:
            raise ValidationError({"dealership_inventory_id": "Position is not available"})
        if not inventory.dealership.is_active:
            raise ValidationError({"dealership_inventory_id": "Dealership is inactive"})
        if inventory.quantity <= 0:
            raise ValidationError({"dealership_inventory_id": "Out of stock"})

        final_price = OfferService.effective_price_for(inventory)

        if buyer.balance < final_price:
            raise ValidationError({"detail": "Insufficient funds"})

        offer = Offer.objects.create(
            buyer=buyer,
            dealership=inventory.dealership,
            dealership_inventory=inventory,
            final_price=final_price,
            status=Offer.Status.CREATED,
        )

        transaction.on_commit(lambda: OfferService.publish_offer_created(offer.id))

        return offer

    @staticmethod
    def publish_offer_created(offer_id: int) -> None:
        from kafka_producer import publish_event

        publish_event(topic=os.getenv("KAFKA_OFFER_TOPIC"), key=offer_id, value={"offer_id": offer_id})
        logger.info("TODO publish offer.created id=%s", offer_id)


class OfferProcessingService:
    """
    Background offer processing — ACTUAL money deduction.
    Called from the `process_offer` Celery task (hybrid approach) or directly (pure scheme).
    """

    @classmethod
    def process(cls, offer_id: int) -> str:
        try:
            offer = Offer.objects.select_related("buyer", "dealership", "dealership_inventory").get(pk=offer_id)
        except Offer.DoesNotExist:
            logger.warning("Offer %s not found", offer_id)
            return "not_found"

        if offer.status != Offer.Status.CREATED:
            logger.info("Offer %s already processed (status=%s), skipping", offer_id, offer.status)
            return "already_processed"

        offer.status = Offer.Status.PROCESSING
        offer.save(update_fields=["status"])

        try:
            return cls.settle(offer)
        except Exception:
            logger.exception("Offer %s settlement crashed", offer_id)
            offer.status = Offer.Status.FAILED
            offer.save(update_fields=["status"])
            return "failed"

    @classmethod
    @transaction.atomic
    def settle(cls, offer: Offer) -> str:
        inventory = (
            DealershipInventory.objects.select_for_update()
            .select_related("dealership")
            .get(pk=offer.dealership_inventory_id)
        )

        if not inventory.dealership.is_active:
            return cls._reject(
                offer=offer,
                reason=Offer.RejectionReason.DEALERSHIP_INACTIVE,  # type: ignore[arg-type]
                message="Dealership became inactive",
            )

        if inventory.quantity <= 0:
            return cls._reject(
                offer=offer,
                reason=Offer.RejectionReason.OUT_OF_STOCK,  # type: ignore[arg-type]
                message="Out of stock at settlement",  # type: ignore[arg-type]
            )

        buyer = offer.buyer
        buyer.refresh_from_db(fields=["balance"])
        if buyer.balance < offer.final_price:
            return cls._reject(
                offer=offer,
                reason=Offer.RejectionReason.INSUFFICIENT_FUNDS,  # type: ignore[arg-type]
                message="Insufficient funds at settlement",
            )

        from buyers.services import BuyerService

        BuyerService.withdraw(buyer, offer.final_price)

        DealershipService.balance_deposit(inventory.dealership, offer.final_price)
        DealershipInventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") - 1)

        offer.status = Offer.Status.PAID
        offer.save(update_fields=["status"])

        logger.info(
            "Offer %s PAID: buyer=%s dealership=%s price=%s",
            offer.pk,
            buyer.pk,
            inventory.dealership_id,
            offer.final_price,
        )
        return "paid"

    @staticmethod
    def _reject(offer: Offer, reason: str, message: str) -> str:
        offer.status = Offer.Status.REJECTED
        offer.rejection_reason = reason
        offer.save(update_fields=["status", "rejection_reason"])
        logger.info("Offer %s REJECTED (%s): %s", offer.pk, reason, message)
        return "rejected"
