from main.lib.gcal import get_gcal_manager
from main.models import *
from main.serializers import *

from django import forms
from django.db.models import Count, Max, Prefetch
from django.http import FileResponse
from rest_framework import exceptions, generics, mixins, parsers, permissions, response, serializers, views, viewsets, renderers
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

import jinja2

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
                'status',
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
    queryset = Cert.objects.select_related('subtype__type')
    serializer_class = CertSerializer
    filterset_fields = ('member', 'member__status__short', 'subtype__type', 'subtype')
    search_fields = ('member__username',  )


def is_valid(cert_list):
    for cert in cert_list:
        if not cert.is_expired:
            return True
    return False

def is_valid_subtype_in(value, cert_list):
    for cert in cert_list:
        if cert.subtype.name == value and not cert.is_expired:
            return True
    return False

class MemberCertViewSet(BaseViewSet):
    serializer_class = MemberCertSerializer
    search_fields = ('username',  )
    ordering = ['last_name']

    def get_queryset(self):
        filter_kwargs = {'status__is_display': True}
        if hasattr(self.request, 'query_params'):
            if self.request.query_params.get('status'):
                filter_kwargs['status__short'] = self.request.query_params['status']
        return Member.objects.filter(**filter_kwargs).prefetch_related(
            'cert_set__subtype__type',
            'role_set',
            'status',
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        env = jinja2.Environment(autoescape=False)
        env.tests["valid"] = is_valid
        env.tests["valid_subtype_in"] = is_valid_subtype_in
        context.update({
            'env': env,
            'display_cert_types': CertType.display_cert_types,
        })
        return context

class EventFilter(filters.FilterSet):
    start_at = filters.DateFromToRangeFilter()
    finish_at = filters.DateFromToRangeFilter()
    start_at_iso = filters.IsoDateTimeFromToRangeFilter(field_name='start_at')
    finish_at_iso = filters.IsoDateTimeFromToRangeFilter(field_name='finish_at')
    is_operation = filters.BooleanFilter(label='Is Operation', method='filter_is_operation')
    class Meta:
        model = Event
        fields = ('type', 'start_at', 'finish_at', 'published',)

    def filter_is_operation(self, queryset, name, value):
        if value:
            return queryset.filter(type='operation')
        else:
            return queryset.exclude(type='operation')



class EventViewSet(BaseViewSet):
    def get_queryset(self):
        qs = Event.objects.all().order_by('-start_at')
        if getattr(self, 'action', None) != 'list':
            # fetch data used by EventDetailSerializer
            qs = qs.prefetch_related(
                "period_set",
                "period_set__participant_set",
                "period_set__participant_set__member",
                "period_set__participant_set__member__status",
                "period_set__participant_set__member__phone_set",
                "period_set__participant_set__member__email_set",
                "period_set__participant_set__member__role_set",
                "operation_type",
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
        "participant_set__member__status",
        "participant_set__member__phone_set",
        "participant_set__member__email_set",
        "participant_set__member__role_set",
    ).all()
    serializer_class = PeriodSerializer


class ParticipantViewSet(CreateListModelMixin, BaseViewSet):
    queryset = Participant.objects.all()
    serializer_class = PeriodParticipantSerializer


class PatrolFilter(filters.FilterSet):
    start_at = filters.DateFromToRangeFilter()
    start_at_iso = filters.IsoDateTimeFromToRangeFilter(field_name='start_at')
    class Meta:
        model = Patrol
        fields = ('member', 'start_at')

class PatrolViewSet(CreateListModelMixin, BaseViewSet):
    queryset = Patrol.objects.all().prefetch_related(
        'member',
        'member__status',
        'member__phone_set',
        'member__email_set',
        'member__role_set',
    )
    serializer_class = PatrolSerializer
    filterset_class = PatrolFilter

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

class DataFileViewSet(BaseViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer

    def perform_create(self, serializer):
        serializer.save(member_id=self.request.user.id)

    @action(methods=['get'], detail=True)
    def download(self, *args, **kwargs):
        instance = self.get_object()
        file_handle = instance.file.open()
        response = FileResponse(file_handle, content_type=instance.content_type)
        response['Content-Length'] = instance.size
        response['Content-Disposition'] = 'attachment; filename="%s"' % instance.name
        return response

# App
class EventNotificationsAvailableViewSet(CreateListModelMixin, BaseViewSet):
    queryset = EventNotificationsAvailable.objects.all()
    ordering = ['position']
    serializer_class = EventNotificationsAvailableSerializer

class RadioChannelsAvailableViewSet(CreateListModelMixin, BaseViewSet):
    queryset = RadioChannelsAvailable.objects.all()
    ordering = ['position']
    serializer_class = RadioChannelsAvailableSerializer

class OperationTypesAvailableViewSet(CreateListModelMixin, BaseViewSet):
    queryset = OperationTypesAvailable.objects.all()
    ordering = ['position']
    serializer_class = OperationTypesAvailableSerializer

class CalloutResponseOptionViewSet(CreateListModelMixin, BaseViewSet):
    queryset = CalloutResponseOption.objects.all()
    ordering = ['position']
    serializer_class = CalloutResponseOptionSerializer

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
        fields = ('status',)


class CalloutViewSet(CreateListModelMixin, BaseViewSet):
    filterset_class = CalloutFilter

    def get_queryset(self):
        queryset = Event.objects.filter(type='operation').select_related(
            'created_by',
            'operation_type',
        ).prefetch_related(
            Prefetch('period_set__calloutresponse_set', queryset=CalloutResponse.objects.filter(member=self.request.user), to_attr='my_response'),
            Prefetch('period_set__calloutresponse_set', to_attr='responses'),
        )
        if getattr(self, 'action', None) != 'list':
            queryset = queryset.prefetch_related(
                'period_set',
                'period_set__calloutresponse_set',
                'period_set__calloutresponse_set__member',
                'period_set__calloutresponse_set__member__phone_set',
                'datafile_set',
                'datafile_set__member',
                'datafile_set__member__phone_set',
            )
        return queryset.annotate(
            calloutlog_count=Count('calloutlog', distinct=True),
            calloutlog_max_id=Max('calloutlog__id'),
            #response_count=Count('period__calloutresponse__response', distinct=True),
        )

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
    queryset = CalloutLog.objects.prefetch_related('member', 'member__phone_set')
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
