import uuid

from django.db import models


class Capsule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey("main.User", on_delete=models.CASCADE)
    title = models.TextField()
    description = models.TextField()

    locked = models.BooleanField(default=False)
    creating = models.BooleanField(default=True)

    members = models.ManyToManyField("main.User", related_name="capsules", blank=True)
    images = models.ManyToManyField("main.Image", related_name="capsules", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
