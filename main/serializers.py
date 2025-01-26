import datetime

from .models import *
from .tasks import message_send, set_do
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from rest_framework import exceptions, serializers
from rest_framework.validators import UniqueTogetherValidator
from collections import defaultdict
from base64 import b64encode, b64decode
from django_q.tasks import async_task

import collections
import dataclasses
import jinja2

import logging
logger = logging.getLogger(__name__)

class WriteOnceMixin:
    """Supports Meta list: write_once_fields = ('a','b')"""
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()

        # Mark fields as read only on PUT/PATCH ('update')
        if 'update' in getattr(self.context.get('view'), 'action', ''):
            for field_name in getattr(self.Meta, 'write_once_fields', None):
                kwargs = extra_kwargs.get(field_name, {})
                kwargs['read_only'] = True
                extra_kwargs[field_name] = kwargs

        return extra_kwargs


class CreatePermModelSerializer(serializers.ModelSerializer):
    """Check object permissions on create."""
    def create(self, validated_data):
        obj = self.Meta.model(**validated_data)
        view = self._context['view']
        request = self._context['request']
        for permission in view.get_permissions():
            if not permission.has_object_permission(request, view, obj):
                raise exceptions.PermissionDenied
        return super(CreatePermModelSerializer, self).create(validated_data)


class PhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = ('id', 'member', 'position', 'type', 'number', 'display_number')

class MemberStatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = MemberStatusType
        fields = ('id', 'short', 'long', 'position', 'color',
                  'is_current', 'is_available', 'is_display',
                  )

class MemberSerializer(serializers.HyperlinkedModelSerializer):
    status = serializers.StringRelatedField()
    phone_set = PhoneSerializer(many=True, read_only=True)
    emp = serializers.CharField(source='v9',
        required=False, allow_blank=True, allow_null=True)
    color = serializers.SerializerMethodField()
    class Meta:
        model = Member
        read_only_fields = ('username', 'full_name', 'status', 'status_order', 'color',
                            'roles', 'role_order',
                            'display_email', 'display_phone', 'short_name', 'last_name',
                            'is_current',  'is_available', 'is_patrol_eligible', 'is_display',
                            'is_unavailable', 'is_staff', 'is_superuser',)
        fields = ('id', 'dl', 'ham', 'emp', 'is_current_do',
                  'last_login', 'phone_set', ) + read_only_fields

    def get_color(self, member):
        return member.status.color


class ParticipantMemberSerializer(serializers.HyperlinkedModelSerializer):
    # does not include is_unavailable since we cannot prefetch it
    status = serializers.StringRelatedField()
    emp = serializers.CharField(source='v9',
        required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = Member
        read_only_fields = ('username', 'full_name', 'status', 'status_order',
                            'roles', 'role_order',
                            'display_email', 'display_phone', 'short_name',
                            'is_staff', 'is_superuser',)
        fields = ('id', 'dl', 'ham', 'emp', 'is_current_do',
                  'last_login',) + read_only_fields


class BareUnavailableSerializer(WriteOnceMixin, serializers.ModelSerializer):
    class Meta:
        model = Unavailable
        write_once_fields = ('member',)
        fields = ('id', 'member', 'start_on', 'end_on', 'comment', )


class MemberUnavailableSerializer(serializers.HyperlinkedModelSerializer):
    busy = serializers.SerializerMethodField()
    status = serializers.StringRelatedField()

    def get_busy(self, member):
        busy = member.filtered_unavailable_set
        return BareUnavailableSerializer(busy, context=self.context, many=True).data

    class Meta:
        model = Member
        read_only_fields = ('full_name', 'status', 'status_order', 'roles', 'role_order')
        fields = ('id', 'busy') + read_only_fields


class CertSerializer(WriteOnceMixin, CreatePermModelSerializer):
    class Meta:
        model = Cert
        read_only_fields = ('is_expired', 'color', 'type_name', 'subtype_name', 'cert_name',)
        write_once_fields = ('member',  )
        fields = ('id', 'expires_on', 'description', 'comment', 'link',
                 ) + read_only_fields + write_once_fields


class MemberCertSerializer(serializers.HyperlinkedModelSerializer):
    certs = serializers.SerializerMethodField()
    status = serializers.StringRelatedField()

    def get_certs(self, member):
        certs = []
        role_names = [r.role for r in member.role_set.all()]
        cert_dict = collections.defaultdict(list)
        for cert in member.cert_set.all():
            if cert.subtype:
                cert_dict[cert.subtype.type.name].append(cert)
        for cert_type in self.context['display_cert_types']:
            if cert_type.template:
                env = self.context['env']
                try:
                    result = cert_type.compiled_template(env).render({
                        'certs': cert_dict[cert_type.name],
                        'all_certs': cert_dict,
                        'roles': role_names,
                    })
                except jinja2.TemplateError:
                    result = 'TemplateError'
                c = DisplayCert()
                c.type = cert_type.name
                c.description = result
                c.count = 1
                certs.append(dataclasses.asdict(c))
            else:
                c = cert_type.get_display_cert(
                    cert_dict[cert_type.name])
                certs.append(dataclasses.asdict(c))
        return certs

    class Meta:
        model = Member
        read_only_fields = ('full_name', 'status', 'status_order')
        fields = ('id', 'certs') + read_only_fields


class DoSerializer(WriteOnceMixin, serializers.ModelSerializer):
    class Meta:
        model = DoAvailable
        read_only_fields = ('start', 'end')
        write_once_fields = ('id', 'year', 'quarter', 'week', 'member')
        fields = ('available', 'assigned', 'comment', ) + read_only_fields + write_once_fields
        validators = [
            UniqueTogetherValidator(
                queryset=DoAvailable.objects.all(),
                fields=('year', 'quarter', 'week', 'member')
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # only the DO planner can assign shifts
        user = getattr(self._context.get('request'), 'user', None)
        if (user is None or
            not user.has_perm('main.change_assigned_for_doavailable')):
            self.fields.get('assigned').read_only = True


class BareParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ('id', 'period', 'member', 'ahc', 'ol', 'en_route_at',
                  'return_home_at', 'signed_in_at', 'signed_out_at')


class ParticipantSerializer(serializers.HyperlinkedModelSerializer):
    member = ParticipantMemberSerializer()

    class Meta:
        model = Participant
        fields = ('id', 'member', 'ahc', 'ol', 'en_route_at',
                  'return_home_at', 'signed_in_at', 'signed_out_at')


class PeriodSerializer(serializers.HyperlinkedModelSerializer):
    participant_set = ParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Period
        fields = ('id', 'position', 'start_at',
                  'finish_at', 'participant_set',)


class EventListSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Event
        fields = ('id', 'title', 'type', 'leaders', 'description', 'location',
                  'lat', 'lon', 'start_at', 'finish_at', 'all_day', 'published',)


class EventDetailSerializer(EventListSerializer):
    period_set = PeriodSerializer(many=True, read_only=True)

    class Meta(EventListSerializer.Meta):
        model = Event
        fields = EventListSerializer.Meta.fields + ('period_set',)


class PeriodParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ('id', 'period', 'member', 'ahc', 'ol', 'en_route_at',
                  'return_home_at', 'signed_in_at', 'signed_out_at')
        validators = [
            UniqueTogetherValidator(
                queryset=Participant.objects.all(),
                fields=('period', 'member')
            )
        ]

    def save(self, **kwargs):
        was_ahc = self.instance is not None and self.instance.ahc
        instance = super().save(**kwargs)
        if instance.ahc and not was_ahc:
            logger.info('Calling set_do {}'.format(instance.member.pk))
            async_task(set_do, instance.member.pk, True)
        return instance



class PatrolSerializer(serializers.ModelSerializer):
    member = ParticipantMemberSerializer(required=False)
    color = serializers.SerializerMethodField()
    class Meta:
        model = Patrol
        fields = ('id', 'member', 'start_at', 'finish_at', 'description', 'color',)

    def get_color(self, patrol):
        return patrol.member.status.color


class DistributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribution
        read_only_fields = ('message',)
        fields = ('id', 'message', 'member', 'send_email', 'send_sms',)


# This version currently requires a period. Future uses can change this.
class MessageListSerializer(serializers.ModelSerializer):
    rsvp_template = serializers.CharField(allow_null=True)

    class Meta:
        model = Message
        read_only_fields = ('author', 'created_at',)
        fields = ('id', 'author', 'text', 'format', 'period',
                  'period_format', 'rsvp_template', 'created_at', 'ancestry',)


class MessageDetailSerializer(MessageListSerializer):
    distribution_set = DistributionSerializer(many=True, required=False)

    class Meta(MessageListSerializer.Meta):
        model = Message
        fields = MessageListSerializer.Meta.fields + ('distribution_set',)

    def create(self, validated_data):
        logger.debug('MessageSerializer.create' + str(validated_data))
        ds_data = validated_data.pop('distribution_set')
        author = self.context['request'].user

        template_str = validated_data.pop('rsvp_template')
        rsvp_template = None
        if template_str:
            try:
                rsvp_template = RsvpTemplate.objects.get(name=template_str)
            except RsvpTemplate.DoesNotExist:
                logger.error('RsvpTemplate {} not found'.format(template_str))

        message = Message.objects.create(
            author=author,
            rsvp_template=rsvp_template,
            **validated_data)
        for distribution_data in ds_data:
            d = message.distribution_set.create(**distribution_data)
        logger.info('Calling message.queue {}'.format(message.pk))
        message.queue()
        logger.info('Calling message_send {}'.format(message.pk))
        async_task(message_send, message.pk)
        logger.debug('MessageSerializer.create done')
        if message.format == 'do_shift_starting':
            logger.info('Calling set_do {}'.format(message.author.pk))
            async_task(set_do, message.author.pk, True)
        return message


class InboundSmsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboundSms
        read_only_fields = ('sid', 'from_number', 'to_number', 'body', 'member', 'outbound', 'yes', 'no', 'extra_info', )
        fields = read_only_fields


class BaseFileSerializer(WriteOnceMixin, CreatePermModelSerializer):
    def create(self, validated_data):
        validated_data['size'] = validated_data['file'].size
        validated_data['name'] = validated_data['file'].name
        if '.' in validated_data['file'].name:
            validated_data['extension'] = validated_data['file'].name.split('.')[-1]
        validated_data['content_type'] = validated_data['file'].content_type
        return super().create(validated_data)


class MemberPhotoSerializer(BaseFileSerializer):
    class Meta:
        model = MemberPhoto
        read_only_fields = ('name', 'extension', 'size', 'content_type')
        write_once_fields = ('member', 'file')
        fields = ('id', 'file', 'member', 'position', 'created_at', 'updated_at', 'name', 'extension', 'size', 'content_type', 'original_url', 'medium_url', 'thumbnail_url', 'gallery_thumb_url')

    file = serializers.ImageField(write_only=True)

    original_url = serializers.SerializerMethodField()
    medium_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    gallery_thumb_url = serializers.SerializerMethodField()

    def get_original_url(self, obj): return self.get_photo_url(obj, 'original')
    def get_medium_url(self, obj): return self.get_photo_url(obj, 'medium')
    def get_thumbnail_url(self, obj): return self.get_photo_url(obj, 'thumbnail')
    def get_gallery_thumb_url(self, obj): return self.get_photo_url(obj, 'gallery_thumb')

    def get_photo_url(self, obj, format):
        url = reverse('member_photo_download', args=[obj.id, format])
        return self.context['request'].build_absolute_uri(url)


# For App

class LocationCoordinatesSerializer(serializers.Serializer):
    lat = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    long = serializers.CharField(source='lon',
        required=False, allow_blank=True, allow_null=True)

class LocationAddressSerializer(serializers.Serializer):
    street = serializers.CharField(source='location_address',
         required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(source='location_city',
         required=False, allow_blank=True, allow_null=True)
    state = serializers.CharField(source='location_state',
         required=False, allow_blank=True, allow_null=True)
    zip = serializers.CharField(source='location_zip',
         required=False, allow_blank=True, allow_null=True)

class LocationSerializer(serializers.Serializer):
    text = serializers.CharField(source='location',
         required=False, allow_blank=True, allow_null=True)
    coordinates = LocationCoordinatesSerializer(source='*', required=False)
    address = LocationAddressSerializer(source='*', required=False)


class CalloutMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ('id', 'first_name', 'last_name', 'full_name', 'username',
                  'mobile_phone')
        read_only_fields = ('mobile_phone',)

class CalloutResponseSerializer(serializers.ModelSerializer):
    member = CalloutMemberSerializer()

    class Meta:
        model = CalloutResponse
        read_only_fields = ('created_at',)
        fields = ('id', 'response', 'member') + read_only_fields

class CalloutResponsePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalloutResponse
        fields = ('id', 'response')


class CalloutPeriodSerializer(serializers.ModelSerializer):
    op = serializers.IntegerField(source='position')
    responses = CalloutResponseSerializer(
        source='calloutresponse_set', many=True, read_only=True)
    class Meta:
        model = Period
        fields = ('id', 'op', 'responses')


class EventNotificationsAvailableSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventNotificationsAvailable
        fields = ('id', 'position', 'name')

class RadioChannelsAvailableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RadioChannelsAvailable
        fields = ('id', 'position', 'name', 'is_primary', 'is_additional')

class OperationTypesAvailableSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationTypesAvailable
        fields = ('id', 'position', 'name', 'enabled', 'icon', 'color')

class CalloutResponseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalloutResponseOption
        fields = ('id', 'position', 'response', 'is_attending', 'color')


class DataFileSerializer(BaseFileSerializer):
    class Meta:
        model = DataFile
        read_only_fields = ('name', 'extension', 'size', 'content_type')
        write_once_fields = ('member', 'file')
        fields = ('id', 'file', 'member', 'event', 'created_at', 'name', 'extension', 'size', 'content_type')
    member = CalloutMemberSerializer(required=False)


class CalloutListSerializer(serializers.ModelSerializer):
    operation_type = serializers.CharField(source='operation_type.name', allow_null=True)
    operation_type_icon = serializers.CharField(source='operation_type.icon', allow_null=True)
    operation_type_color = serializers.CharField(source='operation_type.color', allow_null=True)
    location = LocationSerializer(source='*', required=False)
    my_response = serializers.SerializerMethodField()
    responded = serializers.SerializerMethodField()
    log_count = serializers.SerializerMethodField()
    log_last_id = serializers.SerializerMethodField()

    class Meta:
        model = Event
        read_only_fields = ('created_at',)
        fields = ('id', 'title',
                  'operation_type', 'operation_type_icon', 'operation_type_color',
                  'my_response', 'responded',
                  'log_count', 'log_last_id',
                  'status', 'location',
        ) + read_only_fields

    def create(self, validated_data, **kwargs):
        validated_data['type'] = 'operation'
        return super().create(validated_data, **kwargs)

    def get_my_response(self, obj):
        period = Period.objects.filter(event=obj).order_by('position').first()
        if period is None:
            return None
        try:
            response = CalloutResponse.objects.get(
                period=period, member=self.context['request'].user)
        except KeyError:  # Not being used in a request context - no user available.
            return None
        except ObjectDoesNotExist:  # No response for this user.
            return None
        return response.response

    def get_responded(self, obj):
        return CalloutResponse.objects.filter(period__event=obj).order_by('response').values('response').annotate(total=Count('response'))

    def get_log_count(self, obj):
        return obj.calloutlog_set.all().count()

    def get_log_last_id(self, obj):
        if not self.get_log_count(obj):
            return 0
        return obj.calloutlog_set.order_by('-id').first().id


class CalloutDetailSerializer(CalloutListSerializer):
    operation_type = serializers.SlugRelatedField(slug_field='name', queryset=OperationTypesAvailable.objects.all())
    last_log_timestamp = serializers.SerializerMethodField()
    operational_periods = CalloutPeriodSerializer(
        source='period_set', many=True, read_only=True)
    files = DataFileSerializer(
        source='datafile_set', many=True, read_only=True)
    notifications_made = serializers.SlugRelatedField(
        many=True,
        queryset=EventNotificationsAvailable.objects.all(),
        slug_field='name',
        required=False)
    additional_radio_channels = serializers.SlugRelatedField(
        many=True,
        queryset=RadioChannelsAvailable.objects.all(),
        slug_field='name',
        required=False)
    created_by = CalloutMemberSerializer(required=False, read_only=True)

    class Meta:
        model = Event
        read_only_fields = ('created_by', 'created_at',)
        fields = ('id', 'title', 'operation_type', 'description',
                  'my_response', 'responded',
                  'subject', 'subject_contact',
                  'informant', 'informant_contact',
                  'handling_unit', 'notifications_made',
                  'radio_channel', 'additional_radio_channels',
                  'status', 'resolution',
                  'log_count', 'log_last_id', 'last_log_timestamp',
                  'location',
                  'operational_periods',
                  'files',
        ) + read_only_fields

    def get_last_log_timestamp(self, obj):
        latest = obj.calloutlog_set.filter(event=obj).order_by('-id').first()
        if latest is not None:
            return latest.created_at
        return None


class CalloutLogSerializer(serializers.ModelSerializer):
    member = CalloutMemberSerializer(required=False)
    location = LocationSerializer(source='*', required=False)

    class Meta:
        model = CalloutLog
        read_only_fields = ('created_at',)
        fields = ('id', 'type', 'event', 'member', 'message', 'location', 'update') + read_only_fields
