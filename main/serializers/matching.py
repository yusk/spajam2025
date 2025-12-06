from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from main.models import MatchHistory, User


class MatchPartnerSerializer(serializers.ModelSerializer):
    """Serializer for match partner info."""

    class Meta:
        model = User
        fields = ("id", "name", "icon", "github_icon_url")


class MatchedLanguageSerializer(serializers.Serializer):
    """Serializer for matched language info."""

    name = serializers.CharField()
    icon_url = serializers.CharField()


class MatchResultSerializer(serializers.ModelSerializer):
    """Serializer for match result (used in create/status responses)."""

    partner = serializers.SerializerMethodField()
    remaining_seconds = serializers.SerializerMethodField()
    matched_languages = serializers.SerializerMethodField()

    class Meta:
        model = MatchHistory
        fields = (
            "id",
            "partner",
            "similarity_score",
            "talk_duration",
            "matched_at",
            "remaining_seconds",
            "matched_languages",
        )

    @swagger_serializer_method(serializer_or_field=MatchPartnerSerializer)
    def get_partner(self, obj):
        user = self.context.get("user")
        partner = obj.get_partner(user)
        return MatchPartnerSerializer(partner).data

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_remaining_seconds(self, obj):
        from django.utils import timezone

        if not obj.is_active:
            return 0
        elapsed = (timezone.now() - obj.matched_at).total_seconds()
        remaining = max(0, obj.talk_duration - elapsed)
        return int(remaining)

    @swagger_serializer_method(serializer_or_field=MatchedLanguageSerializer(many=True))
    def get_matched_languages(self, obj):
        from main.services.matching import get_matched_languages

        return get_matched_languages(obj.user1, obj.user2)


class MatchHistorySerializer(serializers.ModelSerializer):
    """Serializer for match history list."""

    partner = serializers.SerializerMethodField()

    class Meta:
        model = MatchHistory
        fields = (
            "id",
            "partner",
            "similarity_score",
            "talk_duration",
            "matched_at",
            "ended_at",
        )

    @swagger_serializer_method(serializer_or_field=MatchPartnerSerializer)
    def get_partner(self, obj):
        user = self.context.get("user")
        partner = obj.get_partner(user)
        return MatchPartnerSerializer(partner).data


class MatchStatusSerializer(serializers.Serializer):
    """Serializer for matching status response."""

    status = serializers.ChoiceField(choices=["free", "talking"])
    match = MatchResultSerializer(required=False, allow_null=True)


class MatchEndResponseSerializer(serializers.Serializer):
    """Serializer for match end response."""

    message = serializers.CharField()


class MatchHistoryResponseSerializer(serializers.Serializer):
    """Serializer for match history response."""

    history = MatchHistorySerializer(many=True)


class MatchErrorSerializer(serializers.Serializer):
    """Serializer for match error response."""

    error = serializers.CharField()


class DebugSimilarityUserSerializer(serializers.Serializer):
    """Serializer for similarity user info."""

    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    similarity_score = serializers.FloatField()
    similarity_percent = serializers.CharField()
    talk_duration_seconds = serializers.IntegerField()
    talk_duration_minutes = serializers.FloatField()
    languages = serializers.ListField(child=serializers.CharField())


class DebugCurrentUserSerializer(serializers.Serializer):
    """Serializer for debug current user info."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    languages = serializers.DictField(child=serializers.IntegerField())


class DebugSimilarityResponseSerializer(serializers.Serializer):
    """Serializer for debug similarity response."""

    current_user = DebugCurrentUserSerializer()
    similarities = DebugSimilarityUserSerializer(many=True)
