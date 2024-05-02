from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from main.lib import push, webhook
from main.models import Event, EventNotificationsAvailable, CalloutResponseOption, CalloutResponse, CalloutLog, Member, Participant
from main.serializers import CalloutDetailSerializer

@receiver(post_save, sender=CalloutResponse)
def response_post_save_handler(sender, instance, created, **kwargs):
    message = '{} responded {}'.format(instance.member, instance.response)
    print(message)
    CalloutLog.objects.create(
        type='response', event=instance.period.event,
        member=instance.member,
        message=message, update=instance.response)
    attending = CalloutResponseOption.check_is_attending(instance.response)
    participant_filter = {'period': instance.period,
                          'member': instance.member}
    if attending:
        Participant.objects.get_or_create(**participant_filter)
    else:
        p = Participant.objects.filter(**participant_filter).first()
        if p:
            p.delete()


def available_member_ids():
    return list(Member.available.values_list('id', flat=True))


def callout_created_handler(instance, title="New Callout"):
    member_ids = available_member_ids()
    push.send_push_message(
        title = title,
        body = instance.title,
        data = { "url": "view-callout", "id": instance.id, "type": "created"},
        member_ids = member_ids,
        channel='callout',
        critical=True)
    webhook.trigger_webhook('callout_created', CalloutDetailSerializer(instance).data)


def callout_resolved_handler(instance):
    member_ids = available_member_ids()
    push.send_push_message(
        title = "Callout Resolved",
        body = instance.resolution,
        data = { "url": "view-callout", "id": instance.id, "type": "log"},
        member_ids = member_ids,
        channel='callout-resolved')


@receiver(post_save, sender=Event)
def event_post_save_handler(sender, instance, created, **kwargs):
    if instance.type != 'operation':
        return
    if created:
        callout_created_handler(instance)
        return
    update = 'Callout updated.'
    history = instance.history.all()[:2]
    delta = history[0].diff_against(history[1])
    if not delta.changes:
        return
    for change in delta.changes:
        if change.field == 'status':
            if change.old =='active' and change.new == 'resolved':
                callout_resolved_handler(instance)
            if change.old =='resolved' and change.new == 'active':
                callout_created_handler(instance, 'Callout reactivated')
        update += "\n{} changed from '{}' to '{}'".format(
            change.field, change.old, change.new)
    CalloutLog.objects.create(
        type='system', event=instance,
        member=history[0].history_user,
        message='', update=update)

@receiver(m2m_changed, sender=Event.notifications_made.through)
def m2m_changed_handler(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        verb = 'added'
    elif action == 'post_remove':
        verb = 'removed'
    else:
        return
    history = instance.history.all()[:2]
    notifications = EventNotificationsAvailable.objects.filter(pk__in=pk_set)
    names = [n.name for n in notifications]
    update = 'Callout updated.\nNotifications {}: {}'.format(verb, names)
    CalloutLog.objects.create(
        type='system', event=instance,
        member=history[0].history_user,
        message='', update=update)
