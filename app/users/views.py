import logging

from django.contrib.auth import get_user_model

from core.views import BaseRegisterView
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from users.utils import LoginThrottle

from .serializers import (
    BuyerRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    DealershipRegistrationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SupplierRegistrationSerializer,
)
from .services import (
    BuyerService,
    DealershipService,
    EmailService,
    PasswordResetService,
    SupplierService,
)


logger = logging.getLogger(__name__)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        logger.info(f"Login attempt: {request.data.get('username')}")
        return super().post(request, *args, **kwargs)


class ConfirmEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uid, token):
        data = EmailService.confirm_email(uid, token)

        return Response(data, status=status.HTTP_200_OK)


class BuyerRegisterView(BaseRegisterView):
    serializer_class = BuyerRegistrationSerializer
    registration_service_method = BuyerService.register_buyer


class SupplierRegisterView(BaseRegisterView):
    serializer_class = SupplierRegistrationSerializer
    registration_service_method = SupplierService.register


class DealershipRegisterView(BaseRegisterView):
    serializer_class = DealershipRegistrationSerializer

    registration_service_method = DealershipService.register


class PasswordResetRequestView(APIView):
    throttle_classes = [LoginThrottle]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService.request_password_reset(email=serializer.validated_data["email"])

        return Response(
            {"message": "If user exists, email was sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PasswordResetService.reset_password(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            password=serializer.validated_data["password"],
        )

        return Response(
            {"message": "Password updated successfully"},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "You are logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
