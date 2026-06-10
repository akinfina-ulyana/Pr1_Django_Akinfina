"""
1. DemandCalculator — calculates demand for one car dealership
2. SupplierOfferResolver — for one model returns a LIST of supplier offers,
   sorted from cheapest to most expensive (taking into account active promotions).
3. AutoPurchaseService — chief orchestrator for one car dealership
4. PrioritySupplierRefresher — The car dealership has an up-to-date list of the "best" suppliers for each model.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Case,
    DecimalField,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from cars.models import CarModel
from dealership.models import (
    Dealership,
    DealershipInventory,
    DealershipPreferredCar,
    PrioritySuppliers,
)
from dealership.services import DealershipService
from suppliers.models import (
    SupplierInventory,
    SupplierPromotion,
    SupplierPromotionItem,
)

from purchases.models import AutoPurchaseLog, SupplierPurchaseTransaction


logger = logging.getLogger(__name__)

DEMAND_WINDOW_DAYS = 30  # sales history for the last X days (e.g. 30)
STOCK_HORIZON_DAYS = 14
TARGET_STOCK_DAYS = 14  # How many days of supply do we want to have AFTER the purchase?
MIN_PURCHASE_QUANTITY = 1
DEFAULT_MARKUP_RATIO = Decimal("1.20")  # Default markup 20%


@dataclass
class DemandItem:
    """What and how much does the car dealership need to purchase?"""

    car_model: CarModel
    current_stock: int
    quantity_to_buy: int
    reason: str


@dataclass
class SupplierOffer:
    """Supplier's offer for the model taking into account the active discount."""

    supplier_inventory: SupplierInventory
    base_price: Decimal
    final_price: Decimal  # base_price * (1 - discount/100)
    discount_percent: Decimal
    available_quantity: int


@dataclass
class PurchaseResult:
    """
    The result of purchasing ONE model (possibly from SEVERAL suppliers).
    Since we can purchase a single model from different suppliers in parts,
    we need an aggregate: how many we ended up purchasing, how many we wanted, and how many
    transactions we conducted.
    """

    quantity_requested: int
    quantity_purchased: int
    transactions_created: int

    @property
    def is_full(self) -> bool:
        return self.quantity_purchased >= self.quantity_requested

    @property
    def is_partial(self) -> bool:
        return 0 < self.quantity_purchased < self.quantity_requested

    @property
    def is_empty(self) -> bool:
        return self.quantity_purchased == 0


class DemandCalculator:
    def __init__(self, dealership: Dealership):
        self.dealership = dealership
        self.now = timezone.now()
        self.window_start = self.now - timedelta(days=DEMAND_WINDOW_DAYS)

    def compute(self) -> list[DemandItem]:
        car_model_ids = self.collect_car_model_ids()
        if not car_model_ids:
            return []

        current_stock_map = self.current_stock_map(car_model_ids)
        sales_map = self.sales_last_window(car_model_ids)
        preferred_map = self.preferred_min_map(car_model_ids)

        car_models = {cm.id: cm for cm in CarModel.objects.filter(id__in=car_model_ids)}

        result: list[DemandItem] = []

        for cm_id in car_model_ids:
            item = self.decide(
                car_model=car_models[cm_id],
                current=current_stock_map.get(cm_id, 0),
                sold=sales_map.get(cm_id, 0),
                preferred_min=preferred_map.get(cm_id, 0),
            )
            if item is not None:
                result.append(item)
        return result

    def collect_car_model_ids(self) -> set[int]:
        ids = set(
            DealershipPreferredCar.objects.filter(dealership=self.dealership, is_active=True).values_list(
                "car_model_id", flat=True
            )
        )
        ids.update(
            DealershipInventory.objects.filter(dealership=self.dealership, is_active=True).values_list(
                "car_model_id", flat=True
            )
        )
        return ids

    def current_stock_map(self, car_model_ids) -> dict[int, int]:
        """How many of each model are currently in stock at the car dealership?"""
        qs = (
            DealershipInventory.objects.filter(
                dealership=self.dealership,
                is_active=True,
                car_model_id__in=car_model_ids,
            )
            .values("car_model_id")
            .annotate(total=Sum("quantity"))
        )
        return {row["car_model_id"]: row["total"] or 0 for row in qs}

    def sales_last_window(self, car_model_ids) -> dict[int, int]:
        from buyers.models import Offer

        qs = (
            Offer.objects.filter(
                dealership=self.dealership,
                status=Offer.Status.PAID,
                created_at__gte=self.window_start,
                dealership_inventory__car_model_id__in=car_model_ids,
            )
            .values("dealership_inventory__car_model_id")
            .annotate(total=Sum(Value(1)))
        )
        return {row["dealership_inventory__car_model_id"]: int(row["total"] or 0) for row in qs}

    def preferred_min_map(self, car_model_ids) -> dict[int, int]:
        qs = DealershipPreferredCar.objects.filter(
            dealership=self.dealership,
            is_active=True,
            car_model_id__in=car_model_ids,
        ).values("car_model_id", "min_quantity")
        return {row["car_model_id"]: row["min_quantity"] for row in qs}

    def decide(self, car_model: CarModel, current: int, sold: int, preferred_min: int) -> DemandItem | None:
        if sold == 0:
            if current >= preferred_min:
                return None
            return DemandItem(
                car_model=car_model,
                current_stock=current,
                quantity_to_buy=max(preferred_min - current, MIN_PURCHASE_QUANTITY),
                reason="preferred_min (no sales history)",
            )

        sales_per_day = Decimal(sold) / Decimal(DEMAND_WINDOW_DAYS)
        days_left = Decimal(current) / sales_per_day if sales_per_day > 0 else Decimal("999")

        if days_left >= STOCK_HORIZON_DAYS:
            return None

        target_stock = int((sales_per_day * Decimal(TARGET_STOCK_DAYS)).quantize(Decimal("1")))
        to_buy = max(target_stock - current, MIN_PURCHASE_QUANTITY)
        return DemandItem(
            car_model=car_model,
            current_stock=current,
            quantity_to_buy=to_buy,
            reason=f"demand_based (sold={sold}/30d, days_left={days_left:.1f})",
        )


class SupplierOfferResolver:
    """
    For a single model, returns a sorted list of all active offers
    from suppliers who have this model in stock.
    """

    def __init__(self, dealership: Dealership):
        self.dealership = dealership
        self.today = timezone.now().date()
        self.priority_supplier_ids = list(
            dealership.priority_suppliers.filter(is_active=True).values_list("supplier_id", flat=True)
        )

    def find_offers(self, car_model: CarModel) -> list[SupplierOffer]:
        """
        Returns all offers for this model, sorted by ascending final price.
        An empty list indicates no offers in stock.
        """
        active_discount_subq = (
            SupplierPromotionItem.objects.filter(
                supplier_inventory=OuterRef("pk"),
                is_active=True,
                supplier_promotion__status=SupplierPromotion.Status.ACTIVE,
                supplier_promotion__is_active=True,
                supplier_promotion__start_date__lte=self.today,
                supplier_promotion__end_date__gte=self.today,
            )
            .order_by("-discount_percent")
            .values("discount_percent")[:1]
        )

        qs = (
            SupplierInventory.objects.filter(
                car_model=car_model, is_active=True, supplier__is_active=True, quantity__gt=0
            )
            .annotate(
                discount=Coalesce(
                    Subquery(active_discount_subq),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=5, decimal_places=2),
                ),
            )
            .annotate(final_price=F("base_price") * (Decimal("1") - F("discount") / Decimal("100")))
            .annotate(
                is_priority=Case(
                    When(supplier_id__in=self.priority_supplier_ids, then=Value(1)),
                    default=Value(0),
                    output_field=DecimalField(),
                ),
            )
            .select_related("supplier", "car_model")
            .order_by("final_price", "-is_priority")
        )

        return [
            SupplierOffer(
                supplier_inventory=inv,
                base_price=inv.base_price,
                final_price=inv.final_price.quantize(Decimal("0.01")),
                discount_percent=inv.discount or Decimal("0"),
                available_quantity=inv.quantity,
            )
            for inv in qs
        ]


class AutoPurchaseService:
    @classmethod
    def process_dealership(cls, dealership_id: int, tick_id: str) -> dict:
        try:
            dealership = Dealership.objects.get(pk=dealership_id, is_active=True)
        except Dealership.DoesNotExist:
            logger.warning("Dealership %s not found or inactive", dealership_id)
            return {"attempted": 0, "fully_purchased": 0, "partial": 0, "failed": 0}

        if AutoPurchaseLog.objects.filter(dealership=dealership, tick_id=tick_id).exists():
            logger.info(
                "Dealership %s already processed for tick %s — skipping",
                dealership_id,
                tick_id,
            )
            return {"attempted": 0, "fully_purchased": 0, "partial": 0, "failed": 0}

        logger.info("Auto-purchase start: dealership=%s tick=%s", dealership_id, tick_id)

        demand_items = DemandCalculator(dealership).compute()
        if not demand_items:
            logger.info("No demand for dealership %s", dealership_id)
            return {"attempted": 0, "fully_purchased": 0, "partial": 0, "failed": 0}

        resolver = SupplierOfferResolver(dealership)
        summary = {"attempted": 0, "fully_purchased": 0, "partial": 0, "failed": 0}

        for item in demand_items:
            summary["attempted"] += 1
            try:
                result = cls.process_one(dealership, item, resolver, tick_id)
                if result.is_full:
                    summary["fully_purchased"] += 1
                elif result.is_partial:
                    summary["partial"] += 1
                else:
                    summary["failed"] += 1
            except Exception as exc:
                logger.exception(
                    "Error processing %s for dealership %s",
                    item.car_model,
                    dealership_id,
                )
                AutoPurchaseLog.objects.create(
                    dealership=dealership,
                    car_model=item.car_model,
                    outcome=AutoPurchaseLog.Outcome.FAILED,
                    quantity_requested=item.quantity_to_buy,
                    message=f"Exception: {exc}",
                    tick_id=tick_id,
                )
                summary["failed"] += 1

        logger.info("Auto-purchase done: dealership=%s %s", dealership_id, summary)
        return summary

    @classmethod
    def process_one(
        cls, dealership: Dealership, item: DemandItem, resolver: SupplierOfferResolver, tick_id: str
    ) -> PurchaseResult:
        offers = resolver.find_offers(item.car_model)
        if not offers:
            AutoPurchaseLog.objects.create(
                dealership=dealership,
                car_model=item.car_model,
                outcome=AutoPurchaseLog.Outcome.SKIPPED_NO_OFFER,
                quantity_requested=item.quantity_to_buy,
                message="No supplier has this model in stock",
                tick_id=tick_id,
            )
            return PurchaseResult(item.quantity_to_buy, 0, 0)

        remaining = item.quantity_to_buy
        total_purchased = 0
        transactions_created = 0
        stopped_reason: str | None = None

        for offer in offers:
            if remaining <= 0:
                break

            to_buy_here = min(remaining, offer.available_quantity)
            dealership.refresh_from_db(fields=["balance"])
            total_cost = (offer.final_price * Decimal(to_buy_here)).quantize(Decimal("0.01"))

            if dealership.balance < total_cost:
                max_affordable = int(dealership.balance / offer.final_price)
                if max_affordable <= 0:
                    stopped_reason = f"insufficient funds: have {dealership.balance}, need {offer.final_price} per unit"
                    break
                to_buy_here = min(to_buy_here, max_affordable)
                total_cost = (offer.final_price * Decimal(to_buy_here)).quantize(Decimal("0.01"))

            try:
                cls.execute_purchase(
                    dealership=dealership,
                    item=item,
                    offer=offer,
                    quantity=to_buy_here,
                    total_cost=total_cost,
                    tick_id=tick_id,
                )
            except StockGoneError as exc:
                AutoPurchaseLog.objects.create(
                    dealership=dealership,
                    car_model=item.car_model,
                    supplier=offer.supplier_inventory.supplier,
                    outcome=AutoPurchaseLog.Outcome.SKIPPED_NO_OFFER,
                    quantity_requested=to_buy_here,
                    message=f"Supplier stock changed during processing: {exc}",
                    tick_id=tick_id,
                )
                continue

            total_purchased += to_buy_here
            remaining -= to_buy_here
            transactions_created += 1

        if remaining > 0:
            outcome = (
                AutoPurchaseLog.Outcome.SKIPPED_NO_FUNDS
                if stopped_reason and "insufficient funds" in stopped_reason
                else AutoPurchaseLog.Outcome.SKIPPED_NO_OFFER
            )
            AutoPurchaseLog.objects.create(
                dealership=dealership,
                car_model=item.car_model,
                outcome=outcome,
                quantity_requested=item.quantity_to_buy,
                quantity_purchased=total_purchased,
                message=(
                    stopped_reason
                    or f"Suppliers exhausted: needed {item.quantity_to_buy}, got {total_purchased}, missing {remaining}"
                ),
                tick_id=tick_id,
            )

        return PurchaseResult(
            quantity_requested=item.quantity_to_buy,
            quantity_purchased=total_purchased,
            transactions_created=transactions_created,
        )

    @classmethod
    @transaction.atomic
    def execute_purchase(
        cls,
        dealership: Dealership,
        item: DemandItem,
        offer: SupplierOffer,
        quantity: int,
        total_cost: Decimal,
        tick_id: str,
    ) -> None:
        inv_locked = SupplierInventory.objects.select_for_update().get(pk=offer.supplier_inventory.pk)
        if inv_locked.quantity < quantity:
            raise StockGoneError(f"requested {quantity}, available now {inv_locked.quantity}")

        DealershipService.balance_withdraw(dealership, total_cost)
        SupplierInventory.objects.filter(pk=inv_locked.pk).update(quantity=F("quantity") - quantity)

        dealership_inv, created = DealershipInventory.objects.get_or_create(
            dealership=dealership,
            car_model=item.car_model,
            defaults={
                "quantity": 0,
                "base_price": offer.final_price,
                "sale_price": (offer.final_price * DEFAULT_MARKUP_RATIO).quantize(Decimal("0.01")),
                "is_active": True,
            },
        )
        if created:
            logger.info(
                "Created new DealershipInventory for dealership=%s car_model=%s with base_price=%s sale_price=%s",
                dealership.pk,
                item.car_model.pk,
                dealership_inv.base_price,
                dealership_inv.sale_price,
            )
        DealershipInventory.objects.filter(pk=dealership_inv.pk).update(quantity=F("quantity") + quantity)

        SupplierPurchaseTransaction.objects.create(
            dealership=dealership,
            supplier=offer.supplier_inventory.supplier,
            supplier_inventory=offer.supplier_inventory,
            car_model=item.car_model,
            quantity=quantity,
            unit_price=offer.final_price,
            total_price=total_cost,
            discount_percent_applied=offer.discount_percent,
        )

        AutoPurchaseLog.objects.create(
            dealership=dealership,
            car_model=item.car_model,
            supplier=offer.supplier_inventory.supplier,
            outcome=AutoPurchaseLog.Outcome.PURCHASED,
            quantity_requested=quantity,
            quantity_purchased=quantity,
            unit_price=offer.final_price,
            message=(f"Reason: {item.reason}; discount={offer.discount_percent}%; total_cost={total_cost}"),
            tick_id=tick_id,
        )

        dealership.priority_suppliers.filter(supplier=offer.supplier_inventory.supplier).update(
            last_deal_at=timezone.now()
        )

        logger.info(
            "Purchased %dx %s from %s for dealership %s, cost=%s",
            quantity,
            item.car_model,
            offer.supplier_inventory.supplier,
            dealership.pk,
            total_cost,
        )


class StockGoneError(Exception):
    """
    Internal exception: supplier stock changed during processing.
    Used to roll back the @transaction.atomic block but allow
    the calling code to proceed with a different supplier (rather than
    falling into a general except block as a genuine error).
    """


class PrioritySupplierRefresher:
    """
    Analyzes current prices. Compares prices. Updates the list of suppliers for the salon.
    """

    @classmethod
    def refresh_for_dealership(cls, dealership: Dealership) -> dict:
        car_model_ids = set(
            DealershipPreferredCar.objects.filter(dealership=dealership, is_active=True).values_list(
                "car_model_id", flat=True
            )
        )
        car_model_ids.update(
            DealershipInventory.objects.filter(dealership=dealership, is_active=True).values_list(
                "car_model_id", flat=True
            )
        )
        if not car_model_ids:
            return {"added": 0, "removed": 0}

        resolver = SupplierOfferResolver(dealership)
        best_supplier_ids: set[int] = set()
        for cm in CarModel.objects.filter(id__in=car_model_ids):
            offers = resolver.find_offers(cm)
            if offers:
                best_supplier_ids.add(offers[0].supplier_inventory.supplier_id)

        existing_ids = set(
            PrioritySuppliers.objects.filter(dealership=dealership, is_active=True).values_list(
                "supplier_id", flat=True
            )
        )

        to_add = best_supplier_ids - existing_ids
        to_remove = existing_ids - best_supplier_ids

        for sup_id in to_add:
            PrioritySuppliers.objects.update_or_create(
                dealership=dealership,
                supplier_id=sup_id,
                defaults={"is_active": True, "note": "auto: best price"},
            )
        if to_remove:
            PrioritySuppliers.objects.filter(dealership=dealership, supplier_id__in=to_remove).update(is_active=False)

        logger.info(
            "PrioritySuppliers refreshed for dealership %s: +%d, -%d",
            dealership.pk,
            len(to_add),
            len(to_remove),
        )
        return {"added": len(to_add), "removed": len(to_remove)}
