from rest_framework import serializers


class GitHubCallbackUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()


class GitHubCallbackResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = GitHubCallbackUserSerializer()


class GitHubCallbackErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
