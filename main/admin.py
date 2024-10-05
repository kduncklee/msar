from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from fcm_django.models import FCMDevice
from fcm_django.admin import DeviceAdmin as FCMDeviceAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import *
from .lib import push

# Register your models here.

class InlineDefaults(admin.TabularInline):
    extra = 0
    min_num = 0

class AddressInline(InlineDefaults):
    model = Address

class EmailInline(InlineDefaults):
    model = Email

class PhoneInline(InlineDefaults):
    model = Phone

class EmergencyContactInline(InlineDefaults):
    model = EmergencyContact

class RoleInline(InlineDefaults):
    model = Role

class OtherInfoInline(InlineDefaults):
    model = OtherInfo

class CertInline(InlineDefaults):
    model=Cert

class MemberUserAdmin(UserAdmin, SimpleHistoryAdmin):
    """Override broken defaults from UserAdmin"""
    fieldsets = None
    search_fields = []
    history_list_display = ["status"]

@admin.register(Member)
class MemberAdmin(MemberUserAdmin):
    list_display = ('last_name', 'first_name', 'status')
    list_filter = ('status', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ['last_name', 'first_name', 'username',]
    inlines = [
        AddressInline,
        EmailInline,
        PhoneInline,
        EmergencyContactInline,
        RoleInline,
        OtherInfoInline,
        CertInline,
        ]


@admin.register(MemberStatusType)
class MemberStatusTypeAdmin(admin.ModelAdmin):
    list_display = ('short','long','position')


class ParticipantInline(InlineDefaults):
    model = Participant

class PeriodInline(InlineDefaults):
    model = Period

@admin.register(Event)
class EventAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'type', 'start_at', 'finish_at',)
    inlines = [
        PeriodInline,
        ]

@admin.register(Period)
class PeriodAdmin(SimpleHistoryAdmin):
    list_display = ('__str__', 'event', 'position', 'start_at', 'finish_at',)
    inlines = [
        ParticipantInline,
        ]


@admin.register(Patrol)
class PatrolAdmin(SimpleHistoryAdmin):
    list_display = ('member', 'start_at',)


@admin.register(EventNotificationsAvailable)
class EventNotificationsAvailableAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(RadioChannelsAvailable)
class RadioChannelsAvailableeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_primary', 'is_additional')


@admin.register(CalloutResponseOption)
class CalloutResponseOptionAdmin(admin.ModelAdmin):
    list_display = ('response', 'is_attending')


@admin.register(CalloutResponse)
class CalloutResponseAdmin(admin.ModelAdmin):
    list_display = ('period', 'created_at', 'member', 'response')
    search_fields = ['member', 'period']

@admin.register(CalloutLog)
class CalloutLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'created_at', 'member', 'message')
    search_fields = ['member', 'event']


class CertSubTypeInline(InlineDefaults):
    model = CertSubType

@admin.register(CertType)
class CertTypeAdmin(admin.ModelAdmin):
    inlines = [
        CertSubTypeInline,
    ]


@admin.register(DoAvailable)
class DoAvailableAdmin(admin.ModelAdmin):
    search_fields = ['member__last_name', 'member__first_name', 'member__username']


class DistributionInline(InlineDefaults):
    model = Distribution


@admin.register(RsvpTemplate)
class RsvpTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'prompt',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('author', 'text', 'created_at',
                    'format', 'period_format', )
    inlines = [
        DistributionInline,
    ]


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'member')
    search_fields = ['name',]

@admin.register(MemberPhoto)
class MemberPhotoAdmin(admin.ModelAdmin):
    list_display = ('name', 'file', 'created_at', 'member')
    search_fields = ['member',]

# Documents
@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('type', 'enabled', 'url')
    readonly_fields = ('url', )

@admin.register(DoLog)
class DoLogAdmin(admin.ModelAdmin):
    list_display = ('year', 'quarter', 'week', 'url',)
    readonly_fields = ('url', )

@admin.register(Aar)
class AarAdmin(admin.ModelAdmin):
    list_display = ('event', 'url',)
    readonly_fields = ('url', )

@admin.register(AhcLog)
class AhcLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'url',)
    readonly_fields = ('url', )

@admin.register(LogisticsSpreadsheet)
class LogisticsSpreadsheetAdmin(admin.ModelAdmin):
    list_display = ('event', 'url',)
    readonly_fields = ('url', )

# FCM
admin.site.unregister(FCMDevice)
@admin.register(FCMDevice)
class CustomFCMDeviceAdmin(FCMDeviceAdmin):
    actions = (
        "enable",
        "disable",
        'send_test_message_callout',
        'send_test_message_callout_resolved',
        'send_test_message_log',
        'send_test_message_announcement',
    )

    def _send_test_message(self, request, queryset, channel, critical=False):
        title = "Test message"
        body = "Sending message type of: " + channel
        push.load_firebase()
        m = push.generate_push_message_firebase(
            title, body, {'title': title, 'body': body}, channel, critical)
        response = push.send_push_message_devices_firebase(queryset, m)
        return self._send_deactivated_message(
                    request, response, len(response.deactivated_registration_ids), False
                )


    def send_test_message_callout(self, request, queryset):
        return self._send_test_message(request, queryset, "callout", True)
    send_test_message_callout.short_description = "Send test message - callout"

    def send_test_message_callout_resolved(self, request, queryset):
        return self._send_test_message(request, queryset, "callout-resolved", True)
    send_test_message_callout_resolved.short_description = "Send test message - callout-resolved"

    def send_test_message_log(self, request, queryset):
        return self._send_test_message(request, queryset, "log")
    send_test_message_log.short_description = "Send test message - log"

    def send_test_message_announcement(self, request, queryset):
        return self._send_test_message(request, queryset, "announcement")
    send_test_message_announcement.short_description = "Send test message - announcement"
