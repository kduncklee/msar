from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from main.models import CalloutLog, OperationTypesAvailable, RemoteServer, RemoteServerAPIKey, Event
from main.serializers import CalloutDetailSerializer, CalloutMemberSerializer
from main.tests.test_member import MemberTestMixin

SERVER_NAME = 'test_server'
OP_TYPE_NAME = 'test_op_type'
EVENT_TITLE = 'Test callout'
RESULT_TITLE = '[{}] {}'.format(SERVER_NAME, EVENT_TITLE)

class TestApi(MemberTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.server, _ = RemoteServer.objects.get_or_create(name=SERVER_NAME)
        remote, self.key = RemoteServerAPIKey.objects.create_key(
            name='test', server=self.server)
        self.op_type, _ = OperationTypesAvailable.objects.get_or_create(name=OP_TYPE_NAME)
    def create_event(self):
        source_event = Event.objects.create(
            type='operation',
            title=EVENT_TITLE,
            status='active',
            operation_type=self.op_type,
            lat=37,
            lon=-118,
        )
        self.event_json = CalloutDetailSerializer(source_event).data
        source_event.delete()
        # print(str(self.event_json))
        return self.event_json

    def url(self, base):
        return '{}?api_key={}'.format(base, self.key)

    def test_bad_key(self):
        response = self.client.post(
            reverse('remote_server'),
            {'unused_arg': 1}, format='json')
        self.assertEqual(response.status_code, 401)
        response = self.client.post(
            reverse('remote_server') + '?api_key=bad_key',
            {'unused_arg': 1}, format='json')
        self.assertEqual(response.status_code, 401)
        response = self.client.post(reverse('remote_created'))
        response = self.client.post(reverse('remote_resolved'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.status_code, 401)
        response = self.client.post(
            reverse('remote_log') + '?api_key=bad_key')
        self.assertEqual(response.status_code, 401)

    def test_server_test(self):
        response = self.client.post(
            self.url(reverse('remote_server')),
            {'unused_arg': 1}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_full_callout(self):
        event_json = self.create_event()
        member_json = CalloutMemberSerializer(self.available_member).data
        count_before = Event.objects.count()

        response = self.client.post(
            self.url(reverse('remote_created')),
            self.event_json, format='json')
        self.assertEqual(response.status_code, 200)
        result_event = Event.objects.order_by('-id').first()
        result_event_id = result_event.id
        self.assertEqual(result_event.title, RESULT_TITLE)
        self.assertEqual(result_event.status, 'active')

        response = self.client.post(
            self.url(reverse('remote_log')),
            {'event': self.event_json,
             'member': member_json,
             'type': 'message',
             'message': 'message 123',
             'update': 'update 123',
             }, format='json')
        self.assertEqual(response.status_code, 200)
        result_event = Event.objects.order_by('-id').first()
        self.assertEqual(result_event.id, result_event_id) # should not make a new copy
        self.assertEqual(result_event.title, RESULT_TITLE)
        result_log = CalloutLog.objects.order_by('-id').first()
        self.assertEqual(result_log.event.id, result_event_id)
        self.assertEqual(result_log.message, 'message 123 - available_member')
        self.assertEqual(result_log.update, 'update 123')

        response = self.client.post(
            self.url(reverse('remote_resolved')),
            self.event_json, format='json')
        self.assertEqual(response.status_code, 200)
        result_event = Event.objects.order_by('-id').first()
        self.assertEqual(result_event.id, result_event_id) # should not make a new copy
        self.assertEqual(result_event.title, RESULT_TITLE)
        self.assertEqual(result_event.status, 'resolved')

        count_after = Event.objects.count()
        self.assertEqual(count_after - count_before, 1)

    def test_log_only(self):
        event_json = self.create_event()
        member_json = CalloutMemberSerializer(self.available_member).data
        count_before = Event.objects.count()

        response = self.client.post(
            self.url(reverse('remote_log')),
            {'event': self.event_json,
             'member': member_json,
             'type': 'message',
             'message': 'message 123',
             'update': 'update 123',
             }, format='json')
        self.assertEqual(response.status_code, 200)
        result_event = Event.objects.order_by('-id').first()
        self.assertEqual(result_event.title, RESULT_TITLE)
        self.assertEqual(result_event.lat, '37')
        result_log = CalloutLog.objects.order_by('-id').first()
        self.assertEqual(result_log.message, 'message 123 - available_member')
        self.assertEqual(result_log.update, 'update 123')

        count_after = Event.objects.count()
        self.assertEqual(count_after - count_before, 1)
