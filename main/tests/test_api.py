from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from main.models import CalloutResponseOption, EventNotificationsAvailable, Member, MemberStatusType, OperationTypesAvailable, Participant
from main.tests.test_member import MemberTestMixin
from unittest.mock import patch

@override_settings(FIREBASE_APP=False, EXPO_APP=True)
class TestApi(MemberTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.uri = '/api/'
        self.other_user = Member.objects.create(
            first_name='Jane',
            last_name='Doe',
            username='jane doe',
            status=MemberStatusType.objects.first(),
        )
        self.no_user = Member.objects.create(
            first_name='No',
            last_name='Status',
            username='r99',
        )
        EventNotificationsAvailable.objects.get_or_create(name='SP')
        OperationTypesAvailable.objects.get_or_create(name='rescue')
        CalloutResponseOption.objects.get_or_create(
            response='10-8', is_attending=True)
        CalloutResponseOption.objects.get_or_create(
            response='10-19', is_attending=True)
        CalloutResponseOption.objects.get_or_create(
            response='10-7', is_attending=False)
        self.member_urls = ['/api/announcement/log/']
        self.callout_urls = ['/api/callouts/']
        self.all_urls = self.member_urls + self.callout_urls

    def test_access_denied(self):
        self.client.force_login(self.user)
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        for endpoint in response.json().values():
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code, 401,
                'Expected 401 forbidden because we are not logged in: ' + endpoint)

    def test_user_access(self):
        self.client.force_login(self.user)
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        for endpoint in list(response.json().values()) + self.all_urls:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code, 200,
                'Expected 200 OK because we are logged in: ' + endpoint)

    def test_available_member_access(self):
        self.client.force_login(self.available_member)
        for url in self.member_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, url)
        for url in self.callout_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)


    def test_filters(self):
        self.client.force_login(self.user)
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.uri + 'members/?status=TM')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.uri + 'member_availability/?status=TM')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.uri + 'operation_types/')
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'rescue')
        self.assertEqual(results[0]['response_time_mode'], 'promised_time')
        response = self.client.get(self.uri + 'callout_responses/')
        self.assertEqual(response.status_code, 200)
        resp_options = response.json()['results']
        self.assertGreaterEqual(len(resp_options), 1)
        self.assertIn('position', resp_options[0])
        self.assertIn('triggers_start_time', resp_options[0])
        self.assertIn('triggers_end_time', resp_options[0])
        self.assertIn('allow_initial', resp_options[0])
        self.assertIn('allowed_from', resp_options[0])
        self.assertEqual(resp_options[0]['compatible_response_time_mode'], '*')

    def _check_event_data(self, data, title, description, responses=0):
        self.assertEqual(data.get('title'), title)
        self.assertEqual(data.get('description'), description)
        op = data.get('operational_periods')[0]
        r = op.get('responses')
        self.assertEqual(len(r), responses)

    def _check_event(self, id, title, description, responses=0):
        response = self.client.get('{}callouts/{}/'.format(self.uri, id),
                                   format='json')
        self.assertEqual(response.status_code, 200)
        self._check_event_data(data=response.data,
                               title=title,
                               description=description,
                               responses=responses)

    @patch('main.lib.push.send_push_message')
    def test_app_flow(self, mock_send_push_message):
        TITLE = 'callout title'
        DESC = 'here is what happened.'
        AVAILABLE_IDS = [self.user.id, self.other_user.id, self.available_member.id]
        self.client.force_login(self.user)
        response = self.client.get(self.uri + '?format=json')
        self.assertEqual(response.status_code, 200)

        # Get initial view - empty
        response = self.client.get(self.uri + 'callouts/?status=active')
        self.assertEqual(response.status_code, 200)
        mock_send_push_message.assert_not_called()

        # Create a callout
        response = self.client.post(
            self.uri + 'callouts/',
            {'title': TITLE,
             'operation_type':'rescue',
             'description': DESC,
             'status': 'active',
             'notifications_made': ['SP'],
             }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_send_push_message.call_count, 2)
        kwargs = mock_send_push_message.call_args_list[0].kwargs
        self.assertEqual(kwargs['title'], 'New Callout')
        self.assertCountEqual(kwargs['member_ids'], AVAILABLE_IDS)
        kwargs = mock_send_push_message.call_args_list[1].kwargs
        self.assertEqual(kwargs['title'], 'Callout updated - john doe')
        mock_send_push_message.reset_mock()
        cid = response.data.get('id')
        self._check_event_data(data=response.data, title=TITLE, description=DESC)
        self._check_event(id=cid, title=TITLE, description=DESC)
        mock_send_push_message.assert_not_called()

        # Log message
        response = self.client.post('{}callouts/{}/log/'.format(self.uri, cid),
                                    {'type':'message', 'message': 'testing'})
        self.assertEqual(response.status_code, 201)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Callout log - john doe')
        self.assertRegex(kwargs['body'], 'testing')
        self.assertCountEqual(kwargs['member_ids'], [self.other_user.id, self.available_member.id])
        mock_send_push_message.reset_mock()
        response = self.client.get('{}callouts/{}/log/'.format(self.uri, cid))
        self.assertEqual(response.status_code, 200)
        logs = response.data.get('results')
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[1].get('type'), 'message')
        self.assertEqual(logs[1].get('message'), 'testing')

        # Check negative response
        response = self.client.post('{}callouts/{}/respond/'.format(self.uri, cid),
                                    {'response': '10-7'})
        self.assertEqual(response.status_code, 200)
        self._check_event(id=cid, title=TITLE, description=DESC, responses=1)
        self.assertEqual(len(Participant.objects.filter(member=self.user)), 0)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Callout log - john doe')
        self.assertEqual(kwargs['member_ids'], [self.other_user.id, self.available_member.id])
        mock_send_push_message.reset_mock()

        # Other user responds yes
        self.client.force_login(self.other_user)
        response = self.client.post('{}callouts/{}/respond/'.format(self.uri, cid),
                                    {'response': '10-8'})
        self.assertEqual(response.status_code, 200)
        self._check_event(id=cid, title=TITLE, description=DESC, responses=2)
        self.assertEqual(len(Participant.objects.filter(member=self.other_user)), 1)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Callout log - jane doe')
        self.assertEqual(kwargs['member_ids'], [self.user.id, self.available_member.id])
        mock_send_push_message.reset_mock()

        # First user responds yes
        self.client.force_login(self.user)
        response = self.client.post('{}callouts/{}/respond/'.format(self.uri, cid),
                                    {'response': '10-8'})
        self.assertEqual(response.status_code, 200)
        self._check_event(id=cid, title=TITLE, description=DESC, responses=2)
        self.assertEqual(len(Participant.objects.filter(member=self.user)), 1)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Callout log - john doe')
        self.assertEqual(kwargs['member_ids'], [self.other_user.id, self.available_member.id])
        mock_send_push_message.reset_mock()

        # Callout complete
        response = self.client.patch('{}callouts/{}/'.format(self.uri, cid),
                                    {'status': 'resolved', 'resolution': 'ok'})
        # print(response.data)
        self.assertEqual(response.status_code, 200)
        mock_send_push_message.assert_called()
        kwargs = mock_send_push_message.call_args_list[0].kwargs
        self.assertEqual(kwargs['title'], 'Callout Resolved')
        self.assertEqual(kwargs['body'], 'ok')
        self.assertCountEqual(kwargs['member_ids'], AVAILABLE_IDS)
        kwargs = mock_send_push_message.call_args_list[1].kwargs
        self.assertEqual(kwargs['title'], 'Callout updated - john doe')
        self.assertRegex(kwargs['body'], 'status')
        self.assertEqual(kwargs['member_ids'], [self.other_user.id, self.available_member.id])
        mock_send_push_message.reset_mock()

        # Callout reopened
        response = self.client.patch('{}callouts/{}/'.format(self.uri, cid),
                                    {'status': 'active', 'resolution': ''})
        self.assertEqual(response.status_code, 200)
        mock_send_push_message.assert_called()
        kwargs = mock_send_push_message.call_args_list[0].kwargs
        self.assertEqual(kwargs['title'], 'Callout reactivated')
        self.assertEqual(kwargs['body'], TITLE)
        self.assertCountEqual(kwargs['member_ids'], AVAILABLE_IDS)
        kwargs = mock_send_push_message.call_args_list[1].kwargs
        self.assertEqual(kwargs['title'], 'Callout updated - john doe')
        self.assertRegex(kwargs['body'], 'status')
        self.assertEqual(kwargs['member_ids'], [self.other_user.id, self.available_member.id])
        mock_send_push_message.reset_mock()

        # Desk creates a new call
        self.client.force_login(self.desk)
        response = self.client.post(
            self.uri + 'callouts/',
            {'title': TITLE + '2',
             'operation_type':'rescue',
             'description': DESC,
             'status': 'active',
             }, format='json')

        self.assertEqual(response.status_code, 201)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'New Callout')
        self.assertCountEqual(kwargs['member_ids'], AVAILABLE_IDS)
        mock_send_push_message.reset_mock()
        cid = response.data.get('id')
        self._check_event_data(data=response.data, title=TITLE + '2', description=DESC)
        self._check_event(id=cid, title=TITLE + '2', description=DESC)
        mock_send_push_message.assert_not_called()

        # Desk log message
        response = self.client.post('{}callouts/{}/log/'.format(self.uri, cid),
                                    {'type':'message', 'message': 'more testing'})
        self.assertEqual(response.status_code, 201)
        mock_send_push_message.assert_called_once()
        kwargs = mock_send_push_message.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Callout log - desk')
        self.assertRegex(kwargs['body'], 'more testing')
        self.assertCountEqual(kwargs['member_ids'], AVAILABLE_IDS)
        mock_send_push_message.reset_mock()

        # Check access for callout notification user
        self.client.force_login(self.available_member)
        response = self.client.get('{}callouts/'.format(self.uri))
        self.assertEqual(response.status_code, 200)
        response = self.client.get('{}callouts/{}/'.format(self.uri, cid))
        self.assertEqual(response.status_code, 200)
        response = self.client.get('{}callouts/{}/log/'.format(self.uri, cid))
        self.assertEqual(response.status_code, 200)

    @patch('main.lib.push.send_push_message')
    def test_callout_respond_times(self, mock_send_push_message):
        self.client.force_login(self.user)
        response = self.client.post(
            self.uri + 'callouts/',
            {
                'title': 'Timed Callout',
                'operation_type': 'rescue',
                'description': 'Testing start_time and end_time',
                'status': 'active',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        cid = response.data['id']

        # Respond 10-19 with start_time
        start_iso = '2026-11-04T14:15:00-08:00'
        response = self.client.post(
            f'{self.uri}callouts/{cid}/respond/',
            {'response': '10-19', 'start_time': start_iso},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        p = Participant.objects.get(member=self.user, period__event_id=cid)
        self.assertIsNotNone(p.signed_in_at)
        self.assertIsNone(p.signed_out_at)

        detail = self.client.get(f'{self.uri}callouts/{cid}/').json()
        resp_entry = detail['operational_periods'][0]['responses'][0]
        self.assertEqual(resp_entry['response'], '10-19')
        self.assertEqual(resp_entry['start_time'], start_iso)
        self.assertIsNone(resp_entry['end_time'])

        # Respond 10-7 with end_time (sign out)
        end_iso = '2026-11-04T18:00:00-08:00'
        response = self.client.post(
            f'{self.uri}callouts/{cid}/respond/',
            {'response': '10-7', 'end_time': end_iso},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        # Participant is preserved with both signed_in_at and signed_out_at
        p.refresh_from_db()
        self.assertIsNotNone(p.signed_in_at)
        self.assertIsNotNone(p.signed_out_at)

        detail = self.client.get(f'{self.uri}callouts/{cid}/').json()
        resp_entry = detail['operational_periods'][0]['responses'][0]
        self.assertEqual(resp_entry['response'], '10-7')
        self.assertEqual(resp_entry['start_time'], start_iso)
        self.assertEqual(resp_entry['end_time'], end_iso)

        # Verify GET /api/callouts/{id}/log/ includes start_time and end_time on response logs
        logs = self.client.get(f'{self.uri}callouts/{cid}/log/').json()['results']
        response_logs = [log for log in logs if log['type'] == 'response']
        self.assertEqual(len(response_logs), 2)
        self.assertEqual(response_logs[0]['update'], '10-19')
        self.assertEqual(response_logs[0]['start_time'], start_iso)
        self.assertIsNone(response_logs[0]['end_time'])
        self.assertEqual(response_logs[1]['update'], '10-7')
        self.assertIsNone(response_logs[1]['start_time'])
        self.assertEqual(response_logs[1]['end_time'], end_iso)
