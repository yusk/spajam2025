from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from main.helpers.jwt import gen_jwt
from main.models import Language, User
from main.serializers import (
    NoneSerializer,
    TokenSerializer,
    UserDeleteSerializer,
    UserGitHubResponseSerializer,
    UserPasswordSerializer,
    UserSerializer,
)
from main.services.matching import get_language_vector


class UserFilter(filters.FilterSet):
    def get_by_tweet_info(self, queryset, name, value):
        kwargs = {f"tweet__{name}": value}
        return queryset.filter(**kwargs).distinct()

    name__gt = filters.CharFilter(field_name="name", lookup_expr="gt")
    name__lt = filters.CharFilter(field_name="name", lookup_expr="lt")
    tweet = filters.CharFilter(method="get_by_tweet_info")

    order_by = filters.OrderingFilter(
        fields=(
            ("id", "id"),
            # ("name", "name"),
        ),
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
        ]


class UserView(GenericAPIView):
    serializer_class = UserSerializer

    @method_decorator(decorator=swagger_auto_schema(responses={200: UserSerializer}))
    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = self.get_serializer(request.user, data=request.data, base64_required=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @method_decorator(
        decorator=swagger_auto_schema(responses={204: NoneSerializer}, request_body=UserDeleteSerializer)
    )
    def delete(self, request):
        serializer = UserDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.request.user
        if not user.check_password(serializer.validated_data["password"]):
            return Response({"password": "password not matched"}, status=400)

        user.delete()
        return Response(None, 204)


class UserPasswordView(GenericAPIView):
    serializer_class = UserPasswordSerializer

    @method_decorator(decorator=swagger_auto_schema(responses={200: TokenSerializer}))
    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.request.user

        if not user.check_password(serializer.validated_data["password"]):
            return Response({"password": "password not matched"}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response({"token": gen_jwt(user)})


class UserViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filter_class = UserFilter
    ordering_fields = ("created_at",)
    ordering = ("created_at",)

    @swagger_auto_schema(
        operation_description="ユーザーのGitHub情報（言語統計含む）を取得します。",
        responses={200: UserGitHubResponseSerializer},
    )
    @action(detail=True, methods=["get"], url_path="github")
    def github(self, request, pk=None):
        """Get user's GitHub information including languages."""
        user = self.get_object()

        # Get GitHub username from repository full_name (format: "owner/repo")
        first_repo = user.repositories.first()
        github_username = None
        if first_repo and first_repo.full_name:
            github_username = first_repo.full_name.split("/")[0]

        # Get language vector
        language_vector = get_language_vector(user)

        # Build language stats with icon URLs
        languages = []
        total_count = sum(language_vector.values()) if language_vector else 0
        for lang_name, count in sorted(language_vector.items(), key=lambda x: x[1], reverse=True):
            try:
                language = Language.objects.get(name=lang_name)
                icon_url = language.icon_url
            except Language.DoesNotExist:
                icon_url = Language.get_devicon_url(lang_name)

            percentage = (count / total_count * 100) if total_count > 0 else 0
            languages.append(
                {
                    "name": lang_name,
                    "icon_url": icon_url,
                    "count": count,
                    "percentage": round(percentage, 1),
                }
            )

        return JsonResponse(
            {
                "user_id": str(user.id),
                "user_name": user.name,
                "github_username": github_username,
                "github_icon_url": user.github_icon_url,
                "total_repos": user.repositories.count(),
                "languages": languages,
            }
        )
