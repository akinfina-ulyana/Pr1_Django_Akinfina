from decimal import Decimal

from dealership.models import DealershipInventory
from rest_framework import serializers

from buyers.models import BuyerProfile, Offer


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = (
            "id",
            "user",
            "first_name",
            "last_name",
            "country",
            "phone",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )


class BalanceOperationSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )


class MarketplaceCarSerializer(serializers.Serializer):
    brand = serializers.CharField()
    model_name = serializers.CharField()
    generation = serializers.CharField()
    body_type = serializers.CharField()
    fuel_type = serializers.CharField()
    transmission = serializers.CharField()
    horsepower = serializers.IntegerField()


class MarketplaceInventorySerializer(serializers.ModelSerializer):
    car = MarketplaceCarSerializer(source="car_model", read_only=True)
    dealership_id = serializers.IntegerField(source="dealership.id", read_only=True)
    dealership_name = serializers.CharField(source="dealership.name", read_only=True)

    discount_percent = serializers.DecimalField(source="discount", max_digits=5, decimal_places=2, read_only=True)
    effective_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = DealershipInventory
        fields = (
            "id",
            "dealership_id",
            "dealership_name",
            "car",
            "sale_price",
            "discount_percent",
            "effective_price",
            "quantity",
        )


class OfferCreateSerializer(serializers.Serializer):
    dealership_inventory_id = serializers.IntegerField()


class OfferReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = (
            "id",
            "dealership",
            "dealership_inventory",
            "final_price",
            "status",
            "rejection_reason",
            "created_at",
        )
        read_only_fields = fields
