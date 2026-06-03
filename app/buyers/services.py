from decimal import Decimal

from django.db.models import F

from rest_framework.exceptions import ValidationError

from buyers.models import BuyerProfile


class BuyerService:
    @staticmethod
    def get_profile_for_user(user) -> BuyerProfile | None:
        """Returns the buyer profile for the user, or None."""
        return getattr(user, "buyer_profile", None)

    @staticmethod
    def update_profile(profile: BuyerProfile, validated_data: dict) -> BuyerProfile:
        for attr, value in validated_data.items():
            setattr(profile, attr, value)
        profile.save()
        return profile

    @staticmethod
    def soft_delete_profile(profile: BuyerProfile) -> None:
        profile.is_active = False
        profile.save(update_fields=["is_active"])

    @staticmethod
    def deposit(profile: BuyerProfile, amount: Decimal) -> BuyerProfile:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        BuyerProfile.objects.filter(pk=profile.pk).update(balance=F("balance") + amount)
        profile.refresh_from_db(fields=["balance"])
        return profile

    @staticmethod
    def withdraw(profile: BuyerProfile, amount: Decimal) -> BuyerProfile:
        if amount <= 0:
            raise ValidationError({"amount": "Must be positive"})

        locked = BuyerProfile.objects.select_for_update().filter(pk=profile.pk).first()
        if locked is None:
            raise ValidationError({"detail": "Profile not found"})
        if locked.balance < amount:
            raise ValidationError({"amount": "Insufficient funds"})

        BuyerProfile.objects.filter(pk=profile.pk).update(balance=F("balance") - amount)
        profile.refresh_from_db(fields=["balance"])
        return profile

    @staticmethod
    def get_balance(profile: BuyerProfile) -> Decimal:
        return profile.balance
