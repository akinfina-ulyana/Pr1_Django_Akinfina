from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BuyerRegisterView,
    ConfirmEmailView,
    CustomTokenObtainPairView,
    DealershipRegisterView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SupplierRegisterView,
    WorkerRegisterView,
)


app_name = "auth"

urlpatterns = [
    path("register/buyer/", BuyerRegisterView.as_view(), name="register-buyer"),
    path("register/supplier/", SupplierRegisterView.as_view(), name="register-supplier"),
    path("register/dealership/", DealershipRegisterView.as_view(), name="register-dealership"),
    path("register/worker/", WorkerRegisterView.as_view(), name="register-worker"),
    path("confirm-email/<uid>/<token>/", ConfirmEmailView.as_view(), name="confirm-email"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="reset-pass"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="confirm-pass"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
]
