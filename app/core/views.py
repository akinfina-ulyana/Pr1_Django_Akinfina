import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response


logger = logging.getLogger(__name__)


class BaseRegisterView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    registration_service_method = None

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        self.registration_service_method(serializer.validated_data)

        return Response(
            {"message": "Check your email to confirm your registration."},
            status=status.HTTP_201_CREATED,
        )
