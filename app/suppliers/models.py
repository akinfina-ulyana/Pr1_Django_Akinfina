from django.db import models

from car_service import settings
from core.base_models import TimeStampedModel


# from app.core.base_models import TimeStampedModel


class Supplier(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает проверки"
        ACTIVE = "active", "Активен"
        SUSPENDED = "suspended", "Приостановлен"
        REJECTED = "rejected", "Отклонён"

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supplier")

    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    founded_year = models.PositiveIntegerField(max_length=4)

    contact_phone = models.CharField(max_length=30, blank=True)
    contact_email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name, self.fo


class WorkerProfileSupplier(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_supplier")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="workers")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100)  # тут лучше сделать Choices
    is_active = models.BooleanField(default=True)


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


# Акции
class SupplierPromotion(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активна"
        EXPIRED = "expired", "Истекла"
        CANCELED = "canceled", "Отменена"

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="promotions")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=True)


# Конкретные скидуи внутри(принадлежащие) акциям
class SupplierPromotionItem(TimeStampedModel):
    supplier_promotion = models.ForeignKey(SupplierPromotion, on_delete=models.CASCADE, related_name="items")
    supplier_inventory = models.ForeignKey(SupplierInventory, on_delete=models.CASCADE, related_name="promotion_items")
    discount_percent = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("supplier_promotion", "supplier_inventory")]
