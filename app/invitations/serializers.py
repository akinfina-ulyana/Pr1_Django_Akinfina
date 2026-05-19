from rest_framework import serializers


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    position = serializers.CharField()

    supplier_id = serializers.IntegerField(required=False)
    dealership_id = serializers.IntegerField(required=False)


class WorkerRegisterSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()
