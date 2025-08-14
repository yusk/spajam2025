from rest_framework import serializers


class UnivUniqueIDSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
