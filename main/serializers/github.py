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
    icon_url = serializers.URLField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class GitHubLanguagesResponseSerializer(serializers.Serializer):
    total_repos = serializers.IntegerField()
    languages = GitHubLanguageSerializer(many=True)


class UserGitHubResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    github_username = serializers.CharField(allow_null=True)
    github_icon_url = serializers.URLField(allow_null=True)
    total_repos = serializers.IntegerField()
    languages = GitHubLanguageSerializer(many=True)
