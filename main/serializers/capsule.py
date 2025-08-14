from rest_framework import serializers

from main.models import Capsule

from .image import ReadImageSerializer
from .user import ReadUserSerializer


class CapsuleSerializer(serializers.ModelSerializer):
    # owner = ReadUserSerializer(read_only=True, required=False)
    members = ReadUserSerializer(many=True, read_only=True)
    images = ReadImageSerializer(many=True, read_only=True)

    class Meta:
        model = Capsule
        fields = (
            "id",
            # "owner",
            "title",
            "description",
            "creating",
            "locked",
            "created_at",
            "members",
            "images",
        )
        depth = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id"].read_only = True
        # self.fields["owner"].read_only = True
        self.fields["creating"].read_only = True
        self.fields["locked"].read_only = True
        # self.fields["created_at"].read_only = True

    # def get_members(self, obj) -> list[str]:
    #     return [d.id for d in obj.members.all()]

    # def get_images(self, obj) -> list[str]:
    #     if obj.locked:
    #         return []
    #     return [self.context["request"].build_absolute_uri(d.image.url) for d in obj.images.all()]
