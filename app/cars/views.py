from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from users.permissions import IsAdmin, IsAnyAuthenticatedRole

from cars.models import CarModel
from cars.serializers import CarModelSerializer
from cars.services import CarService


class CarModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CarModelSerializer

    def get_queryset(self):
        return CarModel.objects.filter(is_active=True)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:  # вот тут исправить  иначе and
            return IsAnyAuthenticatedRole()

        return [IsAdmin()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        CarService.soft_delete(instance)

        return Response({"detail": "CarModel soft deleted"}, status=status.HTTP_200_OK)
