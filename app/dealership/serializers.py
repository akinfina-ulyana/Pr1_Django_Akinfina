from cars.serializers import CarModelSerializer
from rest_framework import serializers

from dealership.models import (
    Dealership,
    DealershipInventory,
    DealershipPreferredCar,
    DealershipPromotion,
    DealershipPromotionItem,
    PrioritySuppliers,
)


class DealershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealership
        fields = (
            "id",
            "name",
            "country",
            "address",
            "description",
            "contact_phone",
            "contact_email",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )


class DealershipInventorySerializer(serializers.ModelSerializer):
    car_model_detail = CarModelSerializer(source="car_model", read_only=True)

    class Meta:
        model = DealershipInventory
        fields = (
            "id",
            "dealership",
            "car_model",
            "car_model_detail",
            "quantity",
            "base_price",
            "sale_price",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "dealership",
            "car_model_detail",
            "is_active",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        base = attrs.get("base_price", getattr(self.instance, "base_price", None))
        sale = attrs.get("sale_price", getattr(self.instance, "sale_price", None))
        if base is not None and sale is not None and sale < base:
            raise serializers.ValidationError({"sale_price": "sale_price cannot be lower than base_price"})
        return attrs


class DealershipPromotionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealershipPromotionItem
        fields = [
            "id",
            "dealership_promotion",
            "dealership_inventory",
            "discount_percent",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_discount_percent(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError("discount_percent must be in (0, 100]")
        return value


class DealershipPromotionSerializer(serializers.ModelSerializer):
    items = DealershipPromotionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DealershipPromotion
        fields = (
            "id",
            "dealership",
            "name",
            "description",
            "start_date",
            "end_date",
            "status",
            "items",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "dealership",
            "status",
            "items",
            "is_active",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "end_date must be greater than or equal to start_date"})
        return attrs


class PrioritySuppliersSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrioritySuppliers
        fields = (
            "id",
            "supplier",
            "dealership",
            "note",
            "contract_start_date",
            "last_deal_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "dealership",
            "last_deal_at",
            "is_active",
            "created_at",
            "updated_at",
        )


class DealershipPreferredCarSerializer(serializers.ModelSerializer):
    car_model_detail = CarModelSerializer(source="car_model", read_only=True)

    class Meta:
        model = DealershipPreferredCar
        fields = (
            "id",
            "dealership",
            "car_model",
            "car_model_detail",
            "min_quantity",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "dealership",
            "car_model_detail",
            "is_active",
            "created_at",
            "updated_at",
        )


class BalanceOperationSerializer(serializers.Serializer):
    from decimal import Decimal

    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
