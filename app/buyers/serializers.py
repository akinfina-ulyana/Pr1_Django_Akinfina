from decimal import Decimal

from rest_framework import serializers

from buyers.models import BuyerProfile


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = [
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
        ]
        read_only_fields = [
            "id",
            "user",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        ]


class BalanceOperationSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
