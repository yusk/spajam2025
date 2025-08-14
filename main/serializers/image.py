from rest_framework import serializers

from main.models import Image

from .base.image import MixInImageBase64Upload


class ImageSerializer(MixInImageBase64Upload, serializers.ModelSerializer):
    # url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = (
            "id",
            "created_at",
            # "url",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id"].read_only = True

    def get_url(self, obj):
        request = self.context["request"]
        url = obj.image.url
        return request.build_absolute_uri(url)


class ReadImageSerializer(serializers.ModelSerializer):
    # url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = (
            "id",
            "created_at",
            "image",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id"].read_only = True
        self.fields["image"].read_only = True
