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


class GitHubLanguageSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class GitHubLanguagesResponseSerializer(serializers.Serializer):
    total_repos = serializers.IntegerField()
    languages = GitHubLanguageSerializer(many=True)
