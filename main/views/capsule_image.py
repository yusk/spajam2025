from django.db.models import Count
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from main.models import Capsule, Image
from main.serializers import ImageSerializer, NoneSerializer, ReadImageSerializer


class CapsuleImageFilter(filters.FilterSet):
    class Meta:
        model = Image
        fields = [
            "id",
        ]


class CapsuleImageViewSet(ModelViewSet):
    serializer_class = ImageSerializer
    filter_class = CapsuleImageFilter
    ordering_fields = ("created_at",)
    ordering = ("created_at",)

    # def get_serializer_context(self):
    #     return super().get_serializer_context()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, capsules=[self.kwargs["capsule_pk"]])

    def get_queryset(self):
        return Image.objects.filter(capsules=self.kwargs["capsule_pk"])

    @action(detail=False, methods=["post"])
    @swagger_auto_schema(request_body=ImageSerializer(many=True), responses={201: ReadImageSerializer(many=True)})
    def bulk(self, request, **kwargs):
        # todo: capsule が creating　ではない場合、エラーになるように
        serializer = ImageSerializer(data=request.data, many=True, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, capsules=[self.kwargs["capsule_pk"]])
        return Response(serializer.data, status=201)

    # @swagger_auto_schema(method="get", responses={200: NoneSerializer})
    # @action(detail=False, methods=["get"], url_path="count")
    # def count(self, request, tweet_pk=None):
    #     res = self.get_queryset().aggregate(Count("id"))
    #     return Response({"count": res["id__count"]}, status=200)
