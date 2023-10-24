from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from main.lib import push
from main.models import Event, EventNotificationsAvailable, CalloutResponse, CalloutLog

@receiver(post_save, sender=CalloutResponse)
def response_post_save_handler(sender, instance, created, **kwargs):
    message = '{} responded {}'.format(instance.member, instance.response)
    CalloutLog.objects.create(
        type='response', event=instance.period.event,
        member=instance.member,
        message=message, update=instance.response)

def callout_created_handler(instance):
    data = {
        "id": instance.id,
        "title": instance.title,
    }
    push.send_push_message(
        title = "MSAR: New Callout",
        body = instance.title)

@receiver(post_save, sender=Event)
def event_post_save_handler(sender, instance, created, **kwargs):
    if instance.type != 'operation':
        return
    if created:
        return
    update = 'Callout updated.'
    history = instance.history.all()[:2]
    delta = history[0].diff_against(history[1])
    if not delta.changes:
        return
    for change in delta.changes:
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

@receiver(post_save, sender=CalloutLog)
def log_post_save_handler(sender, instance, created, **kwargs):
    body = instance.message
    if not body:
        body = instance.update
    push.send_push_message(
        title = "MSAR: New log message",
        body = body)

