from django.conf import settings
from django.db.models import Prefetch
from django import forms
from django.forms import widgets
from django.forms.formsets import BaseFormSet
from django.forms.models import inlineformset_factory, modelform_factory, modelformset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from main.models import Address, Cert, Email, EmergencyContact, Member, MemberStatusType, Phone, Unavailable
from main.views.file_views import download_file_helper

from django.forms.widgets import HiddenInput, Select, Widget, SelectDateWidget

import datetime
from datetime import timedelta

import logging
logger = logging.getLogger(__name__)


from django.utils.html import escape

class MemberStatusTypeMixin:
    def get_context_data(self, *args, **kwargs):
        context = super(MemberStatusTypeMixin, self
                        ).get_context_data(*args, **kwargs)
        context['member_status_types'] = (
            MemberStatusType.displayed.all().order_by('position'))
        return context

class MemberListView(PermissionRequiredMixin, MemberStatusTypeMixin, generic.ListView):
    template_name = 'member_list.html'
    context_object_name = 'member_list'
    permission_required = 'main.view_member'

    def get_queryset(self):
        """Return the member list."""
        return Member.annotate_unavailable(Member.members).order_by(
            'last_name', 'first_name'
        ).prefetch_related(
            'role_set', 'phone_set', 'email_set'
        )


class MemberDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Member
    template_name = 'member_detail.html'
    permission_required = 'main.view_member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class MemberHistoryView(PermissionRequiredMixin, generic.DetailView):
    model = Member
    template_name = 'member_history.html'
    permission_required = 'main.view_member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = Member.objects.get(id=self.kwargs['pk'])
        history = member.history.order_by('history_date')
        last = None
        diffs = []
        for entry in history:
            if last:
                for change in last.diff_against(entry).changes:
                    if change.field == 'status':
                        diffs.append(entry)
            else:
                diffs.append(entry)
            last = entry
        context['diffs'] = diffs
        return context


class MemberPhotoGalleryView(MemberListView):
    template_name = 'member_photo_gallery.html'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'memberphoto_set',
        )


class MemberEditView(PermissionRequiredMixin, generic.base.TemplateView):
    template_name = 'member_edit.html'
    permission_required = 'main.change_member'

    class MemberForm(forms.ModelForm):
        class Meta:
            model = Member
            fields = ('status', 'ham', 'v9', 'dl')
        def __init__(self, user, *args, **kwargs):
            self.user = user
            super().__init__(*args, **kwargs)
        def clean_status(self):
            new_status = self.cleaned_data['status']
            if new_status != self.instance.status:
                logger.info("{} is changing {} to {}.".format(
                    str(self.user), str(self.instance), new_status))
                if not self.user.has_perm('main.change_status_for_member',
                                          self.instance):
                    raise forms.ValidationError("Permission Denied")
            return new_status
    PhonesForm = inlineformset_factory(Member, Phone,
            fields=['type', 'number', 'pagable', 'position'],
            widgets={
                'number': widgets.TextInput(attrs={'placeholder': 'Number'}),
                'position': widgets.HiddenInput(),
            },
            extra=0)
    EmailsForm = inlineformset_factory(Member, Email,
            fields=['type', 'address', 'pagable', 'position'],
            widgets={
                'address': widgets.TextInput(attrs={'placeholder': 'Email address'}),
                'position': widgets.HiddenInput(),
            },
            extra=0)
    AddressesForm = inlineformset_factory(Member, Address,
            fields=['type', 'address1', 'address2', 'city', 'state', 'zip', 'position'],
            widgets={
                'address1': widgets.TextInput(attrs={'placeholder': 'Address line 1'}),
                'address2': widgets.TextInput(attrs={'placeholder': 'Address line 2'}),
                'city': widgets.TextInput(attrs={'placeholder': 'City'}),
                'state': widgets.TextInput(attrs={'placeholder': 'State', 'size': 5}),
                'zip': widgets.TextInput(attrs={'placeholder': 'Zip', 'size': 5}),
                'position': widgets.HiddenInput(),
            },
            extra=0)
    ContactsForm = inlineformset_factory(Member, EmergencyContact,
            fields=['name', 'number', 'type', 'position'],
            widgets={
                'name': widgets.TextInput(attrs={'placeholder': 'Name'}),
                'number': widgets.TextInput(attrs={'placeholder': 'Number'}),
                'position': widgets.HiddenInput(),
            },
            extra=0)

    forms = None

    def get_forms(self, member):
        if self.forms is None:
            if self.request.method == 'POST':
                args = [self.request.POST]
            else:
                args = []
            forms = {}
            forms['member_form'] = self.MemberForm(self.request.user, *args, prefix='member', instance=member)
            forms['phones_form'] = self.PhonesForm(*args, prefix='phones', instance=member)
            forms['emails_form'] = self.EmailsForm(*args, prefix='emails', instance=member)
            forms['addresses_form'] = self.AddressesForm(*args, prefix='addresses', instance=member)
            forms['contacts_form'] = self.ContactsForm(*args, prefix='contacts', instance=member)
            # Hack to prevent undesired behaivour on page refresh: Our
            # javascript modifies the value of TOTAL_FORMS when the user adds a
            # phone/email/etc. If the user then refreshes the page, the browser
            # remembers the incremented TOTAL_FORMS value and restores it. But
            # it does not restore the added form, so submitting results in
            # errors. Setting autocomplete off makes the browser leave
            # TOTAL_FORMS alone.
            for f in forms.values():
                if hasattr(f, 'management_form'):
                    f.management_form.fields['TOTAL_FORMS'].widget.attrs['autocomplete'] = 'off'
            self.forms = forms
        return self.forms

    def get_object(self):
        return Member.objects.get(id=self.kwargs['pk'])

    def post(self, *args, **kwargs):
        member = self.get_object()

        forms = self.get_forms(member)
        for f in forms.values():
            if not f.is_valid():
                logger.info(
                    'MemberEditView {} had invalid form data: {}'.format(
                        repr(f), str(f)))
                return self.get(*args, **kwargs)
        for f in forms.values():
            f.save()

        member.update_google_profile()
        return HttpResponseRedirect(reverse('member_detail', args=[member.id]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        member = Member.objects.get(id=self.kwargs['pk'])
        context['member'] = member
        context.update(self.get_forms(member))
        return context


class MemberAddForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.CharField()
    phone = forms.CharField()


class MemberAddView(PermissionRequiredMixin, generic.edit.FormView):
    """Intended to add guests for trainings.
    Later they can transition to Trainee.
    """
    template_name = 'member_add.html'
    form_class = MemberAddForm
    permission_required = 'main.add_member'

    def form_valid(self, form):
        m, created = Member.objects.get_or_create(
            first_name = form.cleaned_data['first_name'],
            last_name = form.cleaned_data['last_name'],
            defaults={
                'username': '{} {}'.format(
                    form.cleaned_data['first_name'],
                    form.cleaned_data['last_name']).lower(),
                'status': MemberStatusType.objects.get(is_default=True),
                'is_active': False,
            })
        if created:
            Email.objects.create(member=m, pagable=True,
                                 address=form.cleaned_data['email'])
            Phone.objects.create(member=m, pagable=True,
                                 number=form.cleaned_data['phone'])
        return HttpResponseRedirect(m.get_absolute_url())


class MemberPhotoView(PermissionRequiredMixin, generic.DetailView):
    model = Member
    template_name = 'member_photos.html'
    permission_required = 'main.view_memberphoto'

class AvailableListView(PermissionRequiredMixin, MemberStatusTypeMixin, generic.ListView):
    template_name = 'available_list.html'
    context_object_name = 'member_list'
    permission_required = 'main.view_unavailable'

    # TODO split this into a Mixin shared with DoAbstractView and API
    def get_date_param(self, name):
        today = timezone.now().today().date()
        val = self.request.GET.get(name, '')
        setattr(self, name, int(val) if val.isnumeric() else getattr(today,name))

    def get_params(self):
        self.get_date_param('year')
        self.get_date_param('month')
        self.get_date_param('day')
        self.days = int(self.request.GET.get('days', 5))
        self.date = datetime.date(self.year, self.month, self.day)

    def get_queryset(self):
        self.get_params()
        today = self.date
        unavailable_set = Unavailable.objects.filter(
            end_on__gte=today).order_by('start_on')
        qs = Member.members.prefetch_related(
            Prefetch('unavailable_set',
                     queryset=unavailable_set,
                     to_attr='unavailable_filtered'),
            'role_set',
        )

        qs = qs.filter(status__is_available=True).order_by('id')

        for m in qs:
            m.days = ['' for x in range(self.days)]
            for u in m.unavailable_filtered:
                if u.start_on >= today + timedelta(days=self.days):
                    continue  # not in date range
                if u.start_on <= today:
                    start = 0
                else:
                    start = (u.start_on - today).days

                end = (u.end_on - today).days + 1
                if end > self.days:
                    end = self.days
                    m.end_date = u.end_on

                comment = u.comment
                if not comment:
                    comment = 'BUSY'
                for day in range(start, end):
                    m.days[day] = comment
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['days'] = self.days
        context['headers'] = [self.date + timedelta(days=d)
                              for d in range(self.days)]
        return context

class MemberAvailabilityListView(PermissionRequiredMixin, generic.ListView):
    template_name = 'member_availability_list.html'
    context_object_name = 'availability_list'
    permission_required = 'main.view_unavailable'

    def get_queryset(self):
        """Return the availability list."""
        member = Member.objects.get(id=self.kwargs['pk'])
        qs = Unavailable.objects.filter(member=member)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['member'] = Member.objects.filter(id=self.kwargs['pk']).first()
        return context


class DoMemberDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Member
    template_name = 'member_do_availability_list.html'
    permission_required = 'main.view_doavailable'
    

class DoMyAvailabilityView(PermissionRequiredMixin, generic.DetailView):
    template_name = 'member_do_availability_list.html'
    permission_required = 'main.view_doavailable'

    def get_object(self):
        return get_object_or_404(Member, pk=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['member'].direct = True
        return context
