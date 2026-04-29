from django.db import models

from car_service import settings
from core.base_models import TimeStampedModel


class Dealership(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает проверки"
        ACTIVE = "active", "Активен"
        SUSPENDED = "suspended", "Приостановлен"
        REJECTED = "rejected", "Отклонён"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dealership")
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class WorkerProfileDealership(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_dealership")
    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, related_name="workers")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    position = models.CharField(max_length=100)  # ToDo-Choices
    is_active = models.BooleanField(default=True)


class DealershipInventory(TimeStampedModel):
    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, related_name="inventory")
    car_model = models.ForeignKey("cars.CarModel", on_delete=models.PROTECT, related_name="dealership_inventory")
    quantity = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=14, decimal_places=2)
    sale_price = models.DecimalField(max_digits=14, decimal_places=2)
    is_active = models.BooleanField(default=True)


# Вид акции
class DealershipPromotion(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активна"
        EXPIRED = "expired", "Истекла"
        CANCELED = "canceled", "Отменена"

    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, related_name="promotions")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=True)


# Конкретные проценты в рамках акции
class DealershipPromotionItem(TimeStampedModel):
    dealership_promotion = models.ForeignKey(DealershipPromotion, on_delete=models.CASCADE, related_name="items")
    dealership_inventory = models.ForeignKey(
        DealershipInventory, on_delete=models.CASCADE, related_name="promotion_items"
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("dealership_promotion", "dealership_inventory")]


class PrioritySuppliers(TimeStampedModel):
    """Приоритетные поставщики автосалона"""

    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.CASCADE, related_name="priority_links")
    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, related_name="priority_suppliers")
    note = models.TextField(blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    last_deal_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("supplier", "dealership")]
