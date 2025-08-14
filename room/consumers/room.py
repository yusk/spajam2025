import json
import traceback
from dataclasses import dataclass

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from main.models import Capsule
from main.utils import json_serial


@dataclass
class Data:
    members: set
    count: int


data: dict[str, Data] = {}


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.capsule_name = None
        if not self.scope["logged_in_user"].is_authenticated:
            await self.close()
            return
        try:
            user = self.scope["logged_in_user"]
            pk = self.scope["url_route"]["kwargs"]["pk"]
        except KeyError:
            traceback.print_exc()
            await self.close()
            return

        if "latlong" not in self.scope:
            await self.close()
            return
        lat, long = self.scope["latlong"]

        capsule_name = "room_%s" % pk
        await self.channel_layer.group_add(capsule_name, self.channel_name)

        capsule = await database_sync_to_async(Capsule.objects.filter(id=pk, members=user).first)()
        self.pk = pk
        self.capsule = capsule
        self.user = user
        self.capsule_name = capsule_name

        count = await database_sync_to_async(capsule.members.count)()
        if pk not in data:
            data[pk] = Data(set(), count)
        data[pk].count = count
        data[pk].members.add(user.pk)
        d = data[pk]
        print(d)

        await self.accept()

        # todo: 位置情報も扱う

        if len(d.members) == d.count:
            capsule.locked = False
            await database_sync_to_async(capsule.save)()
        body = {"capacity": d.count, "count": len(d.members), "locked": capsule.locked}
        await self.channel_layer.group_send(
            self.capsule_name,
            {"type": "room_message", "message": json.dumps({"content": body}, default=json_serial)},
        )

    async def disconnect(self, close_code):
        if self.capsule_name:
            data[self.pk].members.remove(self.pk)
            print(data)
            await self.channel_layer.group_discard(self.capsule_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass
        # await self.channel_layer.group_send(
        #     self.capsule_name,
        #     {"type": "room_message", "message": json.dumps({"content": text_data}, default=json_serial)},
        # )

    async def room_message(self, event):
        message = event["message"]
        await self.send(text_data=message)
