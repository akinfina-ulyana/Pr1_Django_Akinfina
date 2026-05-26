from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    allowed_roles: set[str] = set()

    def has_permission(self, request, view):
        if not request.auth:
            return False

        role = request.auth.get("role")

        return role in self.allowed_roles


class IsAdmin(HasRole):
    allowed_roles = {"ADMIN"}


class IsBuyer(HasRole):
    allowed_roles = {"BUYER"}


class IsSupplierWorker(HasRole):
    allowed_roles = {"WORKER_SUPPLIER"}


class IsDealershipWorker(HasRole):
    allowed_roles = {"WORKER_DEALERSHIP"}


IsAdminOrSupplierWorker = IsAdmin | IsSupplierWorker
IsAdminOrIsDealershipWorker = IsAdmin | IsDealershipWorker
IsAdminOrBuyer = IsAdmin | IsBuyer
IsAnyAuthenticatedRole = IsAdmin | IsBuyer | IsSupplierWorker | IsDealershipWorker
