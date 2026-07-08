from django.db import models

from car_service import settings
from core.models import TimeStampedModel


class BuyerProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Offer(TimeStampedModel):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PROCESSING = "PROCESSING", "Processing"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        REJECTED = "REJECTED", "Rejected"
        CANCELED = "CANCELED", "Canceled"
        FAILED = "FAILED", "Failed"

    class RejectionReason(models.TextChoices):
        INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS", "Insufficient funds"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of stock"
        DEALERSHIP_INACTIVE = "DEALERSHIP_INACTIVE", "Dealership inactive"

    buyer = models.ForeignKey(BuyerProfile, on_delete=models.PROTECT, related_name="offers")
    dealership = models.ForeignKey("dealership.Dealership", on_delete=models.PROTECT, related_name="offers")
    dealership_inventory = models.ForeignKey(
        "dealership.DealershipInventory", on_delete=models.PROTECT, related_name="offers"
    )
    # max_price = models.DecimalField(max_digits=14, decimal_places=2)
    final_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    rejection_reason = models.CharField(max_length=32, choices=RejectionReason.choices, blank=True)
    is_active = models.BooleanField(default=True)
