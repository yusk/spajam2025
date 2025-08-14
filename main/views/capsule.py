from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from main.models import Capsule
from main.schema import ReadWriteAutoSchema
from main.serializers import CapsuleSerializer, NoneSerializer


class CapsuleFilter(filters.FilterSet):
    order_by = filters.OrderingFilter(
        fields=(
            ("id", "id"),
            ("created_at", "created_at"),
        ),
    )

    class Meta:
        model = Capsule
        fields = [
            "id",
        ]


class CapsuleViewSet(ModelViewSet):
    serializer_class = CapsuleSerializer
    queryset = Capsule.objects.all()
    filter_class = CapsuleFilter
    ordering_fields = ("created_at",)
    ordering = ("created_at",)
    swagger_schema = ReadWriteAutoSchema

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, members=[self.request.user])

    def get_queryset(self):
        return super().get_queryset().filter(members=self.request.user)

    @swagger_auto_schema(request_body=NoneSerializer)
    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        capsule = self.get_object()
        capsule.locked = True
        capsule.creating = False
        capsule.save()
        return Response(self.get_serializer(capsule).data)

    @swagger_auto_schema(request_body=NoneSerializer)
    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        capsule = Capsule.objects.get(pk=pk)
        capsule.members.add(request.user)
        return Response(self.get_serializer(capsule).data)
