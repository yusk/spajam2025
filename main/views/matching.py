from django.db import models
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from main.models import MatchHistory, User
from main.serializers import (
    DebugSimilarityResponseSerializer,
    MatchEndResponseSerializer,
    MatchErrorSerializer,
    MatchHistoryResponseSerializer,
    MatchHistorySerializer,
    MatchResultSerializer,
    MatchStatusSerializer,
)
from main.services.matching import (
    calculate_cosine_similarity,
    create_match,
    get_language_vector,
    get_talk_duration,
)


class MatchingStatusView(APIView):
    @swagger_auto_schema(
        operation_description="現在のマッチング状態を取得します。",
        responses={200: MatchStatusSerializer},
    )
    def get(self, request):
        user = request.user
        active_match = MatchHistory.objects.get_active_match(user)

        if active_match:
            match_data = MatchResultSerializer(active_match, context={"user": user}).data
            return JsonResponse(
                {
                    "status": "talking",
                    "match": match_data,
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "free",
                    "match": None,
                }
            )


class MatchingCreateView(APIView):
    @swagger_auto_schema(
        operation_description="マッチングを生成します。既存のアクティブなマッチがある場合はそれを返します。",
        responses={
            200: MatchResultSerializer,
            404: MatchErrorSerializer,
        },
    )
    def post(self, request):
        user = request.user
        match = create_match(user)

        if not match:
            return JsonResponse(
                {"error": "No available match partner found"},
                status=404,
            )

        match_data = MatchResultSerializer(match, context={"user": user}).data
        return JsonResponse(match_data)


class MatchingEndView(APIView):
    @swagger_auto_schema(
        operation_description="現在のマッチングを終了し、free状態に戻ります。",
        responses={
            200: MatchEndResponseSerializer,
        },
    )
    def post(self, request):
        user = request.user
        active_match = MatchHistory.objects.get_active_match(user)

        if not active_match:
            return JsonResponse({"message": "Match already ended"})

        active_match.end_match()
        return JsonResponse({"message": "Match ended successfully"})


class MatchingHistoryView(APIView):
    @swagger_auto_schema(
        operation_description="今日のマッチング履歴を取得します。",
        responses={200: MatchHistoryResponseSerializer},
    )
    def get(self, request):
        from django.utils import timezone

        user = request.user
        today = timezone.now().date()

        matches = (
            MatchHistory.objects.filter(
                event_date=today,
            )
            .filter(models.Q(user1=user) | models.Q(user2=user))
            .order_by("-matched_at")
        )

        history_data = MatchHistorySerializer(matches, many=True, context={"user": user}).data

        return JsonResponse({"history": history_data})


class MatchingDebugSimilarityView(APIView):
    @swagger_auto_schema(
        operation_description="[デバッグ用] 全ユーザーとの類似度を計算して返します。",
        responses={200: DebugSimilarityResponseSerializer},
    )
    def get(self, request):
        user = request.user
        user_vector = get_language_vector(user)

        # Get all other users
        other_users = User.objects.exclude(id=user.id)

        similarities = []
        for other_user in other_users:
            other_vector = get_language_vector(other_user)
            similarity = calculate_cosine_similarity(user_vector, other_vector)
            talk_duration = get_talk_duration(similarity)

            similarities.append(
                {
                    "user_id": str(other_user.id),
                    "user_name": other_user.name,
                    "similarity_score": round(similarity, 4),
                    "similarity_percent": f"{similarity * 100:.1f}%",
                    "talk_duration_seconds": talk_duration,
                    "talk_duration_minutes": round(talk_duration / 60, 1),
                    "languages": list(other_vector.keys()),
                }
            )

        # Sort by similarity descending
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

        return JsonResponse(
            {
                "current_user": {
                    "id": str(user.id),
                    "name": user.name,
                    "languages": user_vector,
                },
                "similarities": similarities,
            }
        )
