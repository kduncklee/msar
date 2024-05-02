from django.test import TestCase
from django.urls import reverse

from main.models import Member, MemberStatusType, RsvpTemplate
from main.tests.test_member import MemberTestMixin


class AccessTestCase(MemberTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        RsvpTemplate.objects.get_or_create(name='Test',defaults={'prompt':'test'})
        self.urls = [
            reverse('available_list'),
            '/availability/',
            '/member/',
            '/member/{}/'.format(self.user.id),
            '/member/{}/availability/'.format(self.user.id),
            '/file/',
            '/file/upload/',
            '/photos/',
            '/cert/',
            '/member/{}/certs/'.format(self.user.id),
            '/member/{}/certs/new/'.format(self.user.id),
            '/do/schedule/',
            '/message/',
            '/message/add/?page_format=info',
            '/message/test/',
            '/message/inbound/',
            '/action/become_do/',
        ]
        self.user_urls = [
            '/do/my_availability/',
        ]
        self.desk_urls = [
            '/',
            '/event/add/',
            '/desk/callout/',
        ]
        self.event_urls = [
            '/event/',
        ]
        self.all_urls = self.user_urls + self.desk_urls + self.event_urls

    def test_not_logged_in(self):
        for url in self.all_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302,404], url)

    def test_logged_in(self):
        self.client.force_login(self.user)
        for url in self.all_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_desk(self):
        self.client.force_login(self.desk)
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, url)
        for url in self.desk_urls + self.event_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_available_member(self):
        self.client.force_login(self.available_member)
        for url in self.urls + self.user_urls + self.desk_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, url)
        for url in self.event_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
