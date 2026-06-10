from django.db import models
from django.db.models.fields import PositiveIntegerField

from core.models import TimeStampedModel


class SupplierPurchaseTransaction(TimeStampedModel):
    """The fact of purchase by a car dealership from a supplier"""

    dealership = models.ForeignKey(
        "dealership.Dealership", on_delete=models.PROTECT, related_name="purchase_transactions"
    )
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_transactions")
    supplier_inventory = models.ForeignKey(
        "suppliers.SupplierInventory", on_delete=models.PROTECT, related_name="purchase_transactions"
    )
    car_model = models.ForeignKey("cars.CarModel", on_delete=models.PROTECT, related_name="purchase_transactions")
    quantity = PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_percent_applied = models.DecimalField(max_digits=2, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["dealership", "-created_at"]), models.Index(fields=["supplier", "-created_at"])]


class AutoPurchaseLog(TimeStampedModel):
    class Outcome(models.TextChoices):
        PURCHASED = "PURCHASED", "Purchased"
        SKIPPED_NO_OFFER = "SKIPPED_NO_OFFER", "No supplier offer found"
        SKIPPED_NO_FUNDS = "SKIPPED_NO_FUNDS", "Insufficient dealership balance"
        FAILED = "FAILED", "Failed with error"

    dealership = models.ForeignKey(
        "dealership.Dealership",
        on_delete=models.CASCADE,
        related_name="auto_purchase_logs",
    )
    car_model = models.ForeignKey(
        "cars.CarModel",
        on_delete=models.CASCADE,
        related_name="auto_purchase_logs",
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_purchase_logs",
    )
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    quantity_requested = models.PositiveIntegerField(default=0)
    quantity_purchased = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    message = models.TextField(blank=True)
    tick_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["dealership", "-created_at"]),
            models.Index(fields=["tick_id"]),
        ]
