from django.db import models

from core.models import TimeStampedModel


class CarModel(TimeStampedModel):
    class BodyType(models.TextChoices):
        SEDAN = "SEDAN", "Sedan"
        HATCHBACK = "HATCHBACK", "Hatchback"
        SUV = "SUV", "SUV"
        COUPE = "COUPE", "Coupe"
        WAGON = "WAGON", "Station Wagon"
        PICKUP = "PICKUP", "Pickup"
        VAN = "VAN", "Minivan"

    class FuelType(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        HYBRID = "HYBRID", "Hybrid"
        ELECTRIC = "ELECTRIC", "Electric"
        GAS = "GAS", "Gas"

    class Transmission(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"
        ROBOT = "ROBOT", "Automated Manual"
        CVT = "CVT", "CVT"

    class DriveType(models.TextChoices):
        FWD = "FWD", "Front-wheel drive"
        RWD = "RWD", "Rear-wheel drive"
        AWD = "AWD", "All-wheel drive"

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

    def __str__(self):
        return f"{self.brand} {self.model_name} {self.generation}".strip()
