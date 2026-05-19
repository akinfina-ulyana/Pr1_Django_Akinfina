from django.contrib.auth.password_validation import validate_password

from core.serializers import BaseRegistrationSerializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .services import AuthService


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User):
        return AuthService.build_refresh_token(user)


class BuyerRegistrationSerializer(BaseRegistrationSerializer):
    role = User.Role.BUYER

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    country = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)


class SupplierRegistrationSerializer(BaseRegistrationSerializer):
    name = serializers.CharField()
    country = serializers.CharField()
    city = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    founded_year = serializers.IntegerField()


class DealershipRegistrationSerializer(BaseRegistrationSerializer):
    name = serializers.CharField()
    country = serializers.CharField()
    address = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] == attrs["password2"]:
            raise serializers.ValidationError({"password2": "The passwords do not match."})
        return attrs
