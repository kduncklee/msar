from django.db import models
from rest_framework_api_key.models import AbstractAPIKey
from .base import BaseModel
from .event import Event

class RemoteServer(BaseModel):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class RemoteServerAPIKey(AbstractAPIKey):
    server = models.ForeignKey(
        RemoteServer,
        on_delete=models.CASCADE,
        related_name="api_keys",
        related_query_name="api_key",
    )
    class Meta:
        ordering = ("-created",)
        verbose_name = "Remote Server API key"

class RemoteMapping(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    server = models.ForeignKey(RemoteServer, on_delete=models.CASCADE)
    remote_event_id = models.IntegerField()
