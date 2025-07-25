import io
from django.http import HttpResponse
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import BaseHasAPIKey

from main.models import CalloutLog, Event, RemoteMapping, RemoteServer, RemoteServerAPIKey
from main.serializers import CalloutDetailSerializer, CalloutLogSerializer

import logging
logger = logging.getLogger(__name__)


class HasRemoteServerAPIKey(BaseHasAPIKey):
    model = RemoteServerAPIKey

    def get_key(self, request):
        return request.GET.get("api_key")

class AbstractRemoteView(APIView):
    permission_classes = [HasRemoteServerAPIKey]

    def get_server(self, request):
        key = request.GET.get("api_key")
        api_key = RemoteServerAPIKey.objects.get_from_key(key)
        server = RemoteServer.objects.get(api_key=api_key)
        logger.info(server)
        return server

    def process_request(self, request, classname):
        self.server = self.get_server(request)
        logger.info('{}: {}'.format(classname, self.server.name))
        self.post_data = JSONParser().parse(io.BytesIO(request.body))
        return HttpResponse("ok")


class AbstractRemoteCalloutView(AbstractRemoteView):
    def get_or_create_callout(self, server, data):
        remote_event_id = data.get('id') # not in deserialized data
        try:
            mapping = RemoteMapping.objects.get(remote_event_id=remote_event_id)
            event = mapping.event
            callout_serializer = CalloutDetailSerializer(event, data=data)
        except:
            mapping = None
            callout_serializer = CalloutDetailSerializer(data=data)
        finally:
            if not callout_serializer.is_valid():
                logger.error(callout_serializer.errors)
            callout = callout_serializer.validated_data
            remote_event_id = data.get('id') # not in deserialized data
            logger.info('{}: {}'.format(remote_event_id, callout.items()))
            callout['title'] = '[{}] {}'.format(server.name, callout.get('title'))
            callout.pop('additional_radio_channels', None)
            callout.pop('notifications_made', None)

            event = callout_serializer.save()
            if not mapping:
                RemoteMapping.objects.create(
                    event=event,
                    server=server,
                    remote_event_id=remote_event_id)
            return event


class RemoteCalloutCreatedView(AbstractRemoteCalloutView):
    def post(self, request):
        response = self.process_request(request, 'RemoteCalloutCreatedView')
        self.event = self.get_or_create_callout(self.server, self.post_data)
        return response

class RemoteCalloutResolvedView(AbstractRemoteCalloutView):
    def post(self, request):
        response = self.process_request(request, 'RemoteCalloutResolvedView')
        self.post_data['status'] = 'resolved' # force status - don't archive
        self.event = self.get_or_create_callout(self.server, self.post_data)
        return response


class RemoteCalloutLogView(AbstractRemoteCalloutView):
    def post(self, request):
        response = self.process_request(request, 'RemoteCalloutLogView')
        event = self.get_or_create_callout(self.server, self.post_data.get('event'))
        username = self.post_data.get('member', {}).get('username')
        CalloutLog.objects.create(
            type=self.post_data.get('type'),
            event=event,
            message='{} - {}'.format(self.post_data.get('message'), username),
            update=self.post_data.get('update'),
        )
        return response


class ServerTestView(AbstractRemoteView):
    def post(self, request):
        return self.process_request(request, 'ServerTestView')
