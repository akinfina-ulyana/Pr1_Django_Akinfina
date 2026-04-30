from django.db import models

from core.models import TimeStampedModel


class CarModel(TimeStampedModel):
    class BodyType(models.TextChoices):
        SEDAN = "sedan", "Седан"
        HATCHBACK = "hatchback", "Хэтчбек"
        SUV = "suv", "SUV"
        COUPE = "coupe", "Купе"
        WAGON = "wagon", "Универсал"
        PICKUP = "pickup", "Пикап"
        VAN = "van", "Минивэн"

    class FuelType(models.TextChoices):
        PETROL = "petrol", "Бензин"
        DIESEL = "diesel", "Дизель"
        HYBRID = "hybrid", "Гибрид"
        ELECTRIC = "electric", "Электро"
        GAS = "gas", "Газ"

    class Transmission(models.TextChoices):
        MANUAL = "manual", "Механика"
        AUTOMATIC = "automatic", "Автомат"
        ROBOT = "robot", "Робот"
        CVT = "cvt", "Вариатор"

    class DriveType(models.TextChoices):
        FWD = "fwd", "Передний"
        RWD = "rwd", "Задний"
        AWD = "awd", "Полный"

    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    generation = models.CharField(max_length=100, blank=True)
    trim_level = models.CharField(max_length=100, blank=True)
    body_type = models.CharField(max_length=20, choices=BodyType.choices, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, blank=True)
    transmission = models.CharField(max_length=20, choices=Transmission.choices, blank=True)
    drive_type = models.CharField(max_length=10, choices=DriveType.choices, blank=True)
    engine_volume = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    horsepower = models.PositiveIntegerField(null=True, blank=True)
    seat_count = models.PositiveSmallIntegerField(null=True, blank=True)
    door_count = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    production_year_from = models.PositiveIntegerField(null=True, blank=True)
    production_year_to = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["brand", "model_name"])]

    def str(self):
        return f"{self.brand} {self.model_name} {self.generation}".strip()
