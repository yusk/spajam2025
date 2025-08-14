from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from main.helpers import gen_jwt
from main.models import User
from main.serializers import TokenSerializer, UnivUniqueIDSerializer


class RegisterUUIDView(GenericAPIView):
    serializer_class = UnivUniqueIDSerializer
    permission_classes = ()

    @method_decorator(decorator=swagger_auto_schema(responses={200: TokenSerializer}))
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if User.objects.filter(device_uuid=serializer.data["uuid"]):
            message = {"detail": "すでにそのユーザーは登録済みです。"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_guest_user(device_uuid=serializer.data["uuid"])
        user.save()

        serializer = TokenSerializer(data={"token": gen_jwt(user)})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
