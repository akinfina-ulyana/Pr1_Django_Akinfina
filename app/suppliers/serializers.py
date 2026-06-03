from cars.serializers import CarModelSerializer
from rest_framework import serializers

from suppliers.models import (
    Supplier,
    SupplierInventory,
    SupplierPromotion,
    SupplierPromotionItem,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "country",
            "city",
            "address",
            "description",
            "founded_year",
            "contact_phone",
            "contact_email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class SupplierInventorySerializer(serializers.ModelSerializer):
    car_model_detail = CarModelSerializer(source="car_model", read_only=True)

    class Meta:
        model = SupplierInventory
        fields = [
            "id",
            "supplier",
            "car_model",
            "car_model_detail",
            "quantity",
            "base_price",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "supplier", "car_model_detail", "is_active", "created_at", "updated_at"]


class SupplierPromotionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPromotionItem
        fields = [
            "id",
            "supplier_promotion",
            "supplier_inventory",
            "discount_percent",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class SupplierPromotionSerializer(serializers.ModelSerializer):
    items = SupplierPromotionItemSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierPromotion
        fields = [
            "id",
            "supplier",
            "name",
            "description",
            "start_date",
            "end_date",
            "status",
            "items",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "supplier",
            "status",
            "items",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "end_date must be greater than or equal to start_date"})
        return attrs
