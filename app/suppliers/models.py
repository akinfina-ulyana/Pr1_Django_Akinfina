from django.db import models

from car_service import settings
from core.models import TimeStampedModel


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    founded_year = models.PositiveIntegerField()

    contact_phone = models.CharField(max_length=30, blank=True)
    contact_email = models.EmailField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name, self.founded_year


class WorkerProfileSupplier(TimeStampedModel):
    class Position(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        SALES = "SALES", "Sales"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_supplier")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="workers")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    position = models.CharField(
        max_length=50,
        choices=Position.choices,
    )
    is_active = models.BooleanField(default=False)


class SupplierInventory(TimeStampedModel):
    class Currency(models.TextChoices):
        USD = "USD", "USD"
        EUR = "EUR", "EUR"
        BRUB = "BRUB", "BRUB"

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="inventory")
    car_model = models.ForeignKey("cars.CarModel", on_delete=models.PROTECT, related_name="supplier_inventory")
    quantity = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=14, decimal_places=2)

    currency = models.CharField(max_length=4, choices=Currency.choices, default=Currency.USD)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("supplier", "car_model")]


class SupplierPromotion(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="promotions")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=True)


class SupplierPromotionItem(TimeStampedModel):
    supplier_promotion = models.ForeignKey(SupplierPromotion, on_delete=models.CASCADE, related_name="items")
    supplier_inventory = models.ForeignKey(SupplierInventory, on_delete=models.CASCADE, related_name="promotion_items")
    discount_percent = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("supplier_promotion", "supplier_inventory")]
