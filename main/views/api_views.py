from main.lib.gcal import get_gcal_manager
from main.models import *
from main.serializers import *

from django import forms
from django.db.models import Prefetch
from rest_framework import exceptions, generics, mixins, parsers, permissions, response, serializers, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin
from django_filters import rest_framework as filters
import fcm_django.api.rest_framework

import logging
logger = logging.getLogger(__name__)


class FCMDeviceAuthorizedViewSet(fcm_django.api.rest_framework.FCMDeviceAuthorizedViewSet):
    ordering = ['id']


class StrictDjangoObjectPermissions(permissions.DjangoObjectPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
    def get_required_object_permissions(self, method, model_cls):
        p = super().get_required_object_permissions(method, model_cls)
        logger.info(p)
        return p


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = (StrictDjangoObjectPermissions,)
    ordering = ['id']

# From https://stackoverflow.com/a/40253309
class CreateListModelMixin(object):
    def get_serializer(self, *args, **kwargs):
        """ if an array is passed, set serializer to many """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super(CreateListModelMixin, self).get_serializer(*args, **kwargs)


class MemberStatusTypeViewSet(BaseViewSet):
    queryset = MemberStatusType.objects.all()
    serializer_class = MemberStatusTypeSerializer


class MemberViewSet(BaseViewSet):
    serializer_class = MemberSerializer
    search_fields = ('username',  )

    def get_queryset(self):
        filter_kwargs = {}
        if hasattr(self.request, 'query_params'):
            if self.request.query_params.get('status'):
                filter_kwargs['status__short'] = self.request.query_params['status']
        return Member.annotate_unavailable(
            Member.objects).filter(**filter_kwargs).prefetch_related(
                'email_set',
                'phone_set',
                'role_set',
            )


class UnavailableFilter(filters.FilterSet):
    start_on = filters.DateFromToRangeFilter()
    class Meta:
        model = Unavailable
        fields = ('member__status__short', 'start_on', )


class ApiUnavailableViewSet(BaseViewSet):
    queryset = Unavailable.objects.all()
    serializer_class = BareUnavailableSerializer
    filterset_class = UnavailableFilter
    search_fields = ('member__username', )


class MemberUnavailableViewSet(BaseViewSet):
    serializer_class = MemberUnavailableSerializer
    search_fields = ('username',  )

    def get_queryset(self):
        member_filter_kwargs = {}
        filter_kwargs = {}
        if hasattr(self.request, 'query_params'):
            if self.request.query_params.get('status'):
                member_filter_kwargs['status__short'] = self.request.query_params['status']
            if self.request.query_params.get('date_range_start'):
                filter_kwargs['end_on__gte'] = forms.DateField().clean(
                        self.request.query_params['date_range_start'])
            if self.request.query_params.get('date_range_end'):
                filter_kwargs['start_on__lte'] = forms.DateField().clean(
                        self.request.query_params['date_range_end'])
        return Member.members.filter(**member_filter_kwargs).prefetch_related(
            'role_set',
            Prefetch('unavailable_set', queryset=Unavailable.objects.filter(**filter_kwargs), to_attr='filtered_unavailable_set'),
        )


class CertViewSet(BaseViewSet):
    queryset = Cert.objects.all()
    serializer_class = CertSerializer
    filterset_fields = ('member__status__short', 'type', )
    search_fields = ('member__username',  )


class MemberCertViewSet(BaseViewSet):
    queryset = Member.objects.prefetch_related('cert_set')
    serializer_class = MemberCertSerializer
    filterset_fields = ('status__short', )
    search_fields = ('username',  )


class EventFilter(filters.FilterSet):
    start_at = filters.DateFromToRangeFilter()
    finish_at = filters.DateFromToRangeFilter()
    start_at_iso = filters.IsoDateTimeFromToRangeFilter(field_name='start_at')
    finish_at_iso = filters.IsoDateTimeFromToRangeFilter(field_name='finish_at')
    class Meta:
        model = Event
        fields = ('type', 'start_at', 'finish_at', 'published',)


class EventViewSet(BaseViewSet):
    def get_queryset(self):
        qs = Event.objects.all().order_by('-start_at')
        if getattr(self, 'action', None) != 'list':
            # fetch data used by EventDetailSerializer
            qs = qs.prefetch_related(
                "period_set",
                "period_set__participant_set",
                "period_set__participant_set__member",
                "period_set__participant_set__member__phone_set",
                "period_set__participant_set__member__email_set",
                "period_set__participant_set__member__role_set",
            )
        return qs

    filterset_class = EventFilter
    search_fields = ('title', 'description', 'location', )

    def get_serializer_class(self):
        if getattr(self, 'action', None) == 'list':
            return EventListSerializer
        return EventDetailSerializer

    def perform_create(self, serializer):
        super(EventViewSet, self).perform_create(serializer)
        get_gcal_manager().sync_event(serializer.instance)

    def perform_update(self, serializer):
        super(EventViewSet, self).perform_update(serializer)
        get_gcal_manager().sync_event(serializer.instance)

    def perform_destroy(self, event):
        get_gcal_manager().delete_for_event(event)
        super(EventViewSet, self).perform_destroy(event)


class PeriodViewSet(BaseViewSet):
    queryset = Period.objects.prefetch_related(
        "participant_set",
        "participant_set__member",
        "participant_set__member__phone_set",
        "participant_set__member__email_set",
        "participant_set__member__role_set",
    ).all()
    serializer_class = PeriodSerializer


class ParticipantViewSet(CreateListModelMixin, BaseViewSet):
    queryset = Participant.objects.all()
    serializer_class = PeriodParticipantSerializer


class PatrolViewSet(CreateListModelMixin, BaseViewSet):
    queryset = Patrol.objects.all()
    serializer_class = PatrolSerializer
    filterset_fields = ('member', 'date')

    def perform_create(self, serializer):
        serializer.save(member_id=self.request.user.id)


class DoViewSet(BaseViewSet):
    queryset = DoAvailable.objects.all().order_by('week')
    serializer_class = DoSerializer
    filterset_fields = ('year', 'quarter', 'week', 'available', 'assigned',
                     'comment', 'member', )
    search_fields = ('member__username',)

    def list(self, request, *args, **kwargs):
        id = request.query_params.get('member', None)
        if id is not None:
            try:
                member = Member.objects.filter(id=id)[0]
            except:
                content = {'Bad param': 'Invalid member id'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)
        else:
            member = None

        year = request.query_params.get('year', None)
        if year is not None:
            try:
                year = int(year)
                if year < 2010 or year > 2030:
                    raise
            except:
                content = {'Bad param': 'Invalid year'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        quarter = request.query_params.get('quarter', None)
        if quarter is not None:
            try:
                quarter = int(quarter)
                if quarter < 1 or quarter > 4:
                    raise
            except:
                content = {'Bad param': 'Invalid quarter'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        # If the request is a member and a specific quarter,
        # create all the objects for that quarter
        #import pdb; pdb.set_trace()
        if member is not None and year is not None and quarter is not None:
            for week in DoAvailable.weeks(year, quarter):
                availability, created = DoAvailable.objects.get_or_create(
                    member=member, year=year, quarter=quarter, week=week)
                if created:
                    availability.save()

        return super(DoViewSet, self).list(self, request, *args, **kwargs)


class MessageFilter(filters.FilterSet):
    created_at = filters.DateFromToRangeFilter()
    class Meta:
        model = Message
        fields = ('created_at', )


class MessageViewSet(BaseViewSet):
    queryset = Message.objects.all().prefetch_related(
        'author',
        'author__email_set',
        'author__phone_set',
        'author__role_set',
        'rsvp_template',
    )
    filterset_class = MessageFilter
    search_fields = ('author__username',)
    def get_serializer_class(self):
        if getattr(self, 'action', None) == 'list':
            return MessageListSerializer
        return MessageDetailSerializer


class InboundSmsViewSet(BaseViewSet):
    queryset = InboundSms.objects.all()
    serializer_class = InboundSmsSerializer
    filterset_fields = ('member', 'outbound', 'outbound__distribution__message__period')
    search_fields = ('member__username', )


class MemberPhotoViewSet(BaseViewSet):
    queryset = MemberPhoto.objects.all()
    serializer_class = MemberPhotoSerializer
    filterset_fields = ('member', )
    search_fields = ('member__username', )

# App
class EventNotificationsAvailableViewSet(CreateListModelMixin, BaseViewSet):
    queryset = EventNotificationsAvailable.objects.all()
    serializer_class = EventNotificationsAvailableSerializer

class RadioChannelsAvailableViewSet(CreateListModelMixin, BaseViewSet):
    queryset = RadioChannelsAvailable.objects.all()
    serializer_class = RadioChannelsAvailableSerializer

class CreateListNestedViewSetMixin(CreateListModelMixin, NestedViewSetMixin):
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            data.update(parents_query_dict)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CalloutFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Event.STATUS_TYPES)
    class Meta:
        model = Event
        fields = ('status', 'operation_type')


class CalloutViewSet(CreateListModelMixin, BaseViewSet):
    queryset = Event.objects.filter(type='operation').prefetch_related(
        'created_by',
        'period_set',
        'period_set__calloutresponse_set',
        'period_set__calloutresponse_set__member',
        'calloutlog_set')
    filterset_class = CalloutFilter

    def get_serializer_class(self):
        if getattr(self, 'action', None) == 'list':
            return CalloutListSerializer
        elif getattr(self, 'action', None) == 'respond':
            return CalloutResponsePostSerializer
        return CalloutDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id)

    @action(methods=['post'], detail=True)
    def respond(self, request, pk=None):
        period = Period.objects.filter(event=pk).order_by('position').first()
        if period is None:
            raise serializers.ValidationError('No matching Period found.')
        response = request.data['response']
        obj, created = CalloutResponse.objects.get_or_create(
            period=period,
            member=request.user,
            defaults={'response': response},
        )
        # Only update if changed - this suppresses duplication notifications
        if not created and obj.response != response:
            obj.response = response
            obj.save()
        return Response(obj.pk)


class CalloutResponseViewSet(CreateListModelMixin, BaseViewSet):
    queryset = CalloutResponse.objects.all()
    serializer_class = CalloutResponseSerializer


class CalloutLogViewSet(CreateListNestedViewSetMixin, BaseViewSet):
    queryset = CalloutLog.objects.prefetch_related('member')
    serializer_class = CalloutLogSerializer

    def perform_create(self, serializer):
        serializer.save(member_id=self.request.user.id)

class AnnouncementsPermissions(permissions.DjangoObjectPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_announcement"],
        "OPTIONS": ["%(app_label)s.view_announcement"],
        "HEAD": ["%(app_label)s.view_announcement"],
        "POST": ["%(app_label)s.add_announcement"],
        "PUT": ["%(app_label)s.change_announcement"],
        "PATCH": ["%(app_label)s.change_announcement"],
        "DELETE": ["%(app_label)s.delete_announcement"],
    }

class AnnouncementLogViewSet(CalloutLogViewSet):
    permission_classes = (AnnouncementsPermissions,)
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(event__isnull=True)

    def perform_create(self, serializer):
        serializer.save(member_id=self.request.user.id, event=None)
