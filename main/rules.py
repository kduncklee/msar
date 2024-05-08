import rules

import logging
logger = logging.getLogger(__name__)

# Predicates are only used in this file

@rules.predicate
def is_current_member(user):
    return (user.is_authenticated and
            user.status.is_current)

@rules.predicate
def is_available_member(user):
    return (user.is_authenticated and
            user.status.is_available)

@rules.predicate
def is_member_self(user, member): # only for Member
    return member == user

@rules.predicate
def is_owner(user, obj):  # For models with a member field
    if not user.is_authenticated:
        return False
    if obj is None: # If non-object permission, we accept it
        return True
    if not hasattr(obj, 'member'):
        return False
    return obj.member == user

@rules.predicate
def can_add_member(user):
    return (user.is_authenticated and
            user.role_set.filter(role__in=['RO',]).exists())

@rules.predicate
def is_member_editor(user):
    return (user.is_authenticated and
            user.role_set.filter(role__in=['SEC', 'OO', 'RO',]).exists())

@rules.predicate
def is_cert_editor(user):
    return (user.is_authenticated and
            user.role_set.filter(role__in=['SEC', 'OO',]).exists())

@rules.predicate
def is_do_planner(user):
    return (user.is_authenticated and
            user.role_set.filter(role__in=['DOS',]).exists())

@rules.predicate
def is_desk(user):
    return (user.is_authenticated and
            user.status.short == 'DESK')


# Permissions are used in views and templates. Follow the Django
# naming scheme where possible: add_X, view_X, change_X, delete_X

rules.add_perm('main', is_current_member | is_desk)

# Access to generation of reports
rules.add_perm('main.view_report', is_current_member)

rules.add_perm('main.add_member', can_add_member)
rules.add_perm('main.view_member', is_member_self | is_current_member)
rules.add_perm('main.change_member', is_current_member & is_member_self | is_member_editor)
rules.add_perm('main.change_status_for_member', is_member_editor)
rules.add_perm('main.change_certs_for_member', is_member_self | is_cert_editor)

# Message models - anyone can send, backend does receive
rules.add_perm('main.add_message', is_current_member)
for model in ['message', 'inboundsms',]:
    rules.add_perm('main.view_%s' % model, is_current_member)

# Plan the DO calendar
rules.add_perm('main.add_doavailable', is_current_member)
rules.add_perm('main.view_doavailable', is_current_member)
rules.add_perm('main.change_doavailable', is_owner | is_do_planner)
rules.add_perm('main.change_assigned_for_doavailable', is_do_planner)

# Need owner to create. These need CreatePermModelSerializer
for model in ['memberphoto', ]:
    rules.add_perm('main.add_%s' % model, is_owner)
    rules.add_perm('main.view_%s' % model, is_current_member)
    rules.add_perm('main.change_%s' % model, is_owner)
    rules.add_perm('main.delete_%s' % model, is_owner)

rules.add_perm('main.add_datafile', is_current_member)
rules.add_perm('main.view_datafile', is_current_member)

rules.add_perm('main.add_cert', is_current_member & is_owner | is_cert_editor)
rules.add_perm('main.view_cert', is_current_member)
rules.add_perm('main.change_cert', is_owner | is_cert_editor)
rules.add_perm('main.delete_cert', is_owner | is_cert_editor)


# Simple owner models
for model in ['unavailable', 'patrol', 'calloutresponse']:
    rules.add_perm('main.add_%s' % model, is_current_member)
    rules.add_perm('main.view_%s' % model, is_current_member)
    rules.add_perm('main.change_%s' % model, is_owner)
    rules.add_perm('main.delete_%s' % model, is_owner)

# Models with open permission
for model in ['event', 'period', 'participant', ]:
    rules.add_perm('main.add_%s' % model, is_current_member | is_desk)
    rules.add_perm('main.view_%s' % model, is_current_member | is_desk | is_available_member)
    rules.add_perm('main.change_%s' % model, is_current_member | is_desk)
    rules.add_perm('main.delete_%s' % model, is_current_member)

for model in ['calloutlog', ]:
    rules.add_perm('main.add_%s' % model, is_current_member | is_desk)
    rules.add_perm('main.view_%s' % model, is_current_member | is_desk | is_available_member)

for model in ['announcement', ]:
    rules.add_perm('main.add_%s' % model, is_current_member)
    rules.add_perm('main.view_%s' % model, is_current_member)

rules.add_perm('main.desk', is_current_member | is_desk)

# Read-only configurations
rules.add_perm('main.view_memberstatustype', rules.is_authenticated)
rules.add_perm('main.view_eventnotificationsavailable', rules.is_authenticated)
rules.add_perm('main.view_radiochannelsavailable', rules.is_authenticated)
