from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from main.models import Event

import logging
logger = logging.getLogger(__name__)


class CalloutForm(ModelForm):
    class Meta:
        model = Event
        fields = [
            'handling_unit',
            'operation_type', 'title', 'description',
            'location', 'lat', 'lon',
            'location_address', 'location_city',
            'subject', 'subject_contact', 'informant', 'informant_contact',
            'radio_channel',
            'notifications_made',
        ]

class DeskCalloutBaseView(PermissionRequiredMixin, generic.edit.ModelFormMixin):
    model = Event
    form_class = CalloutForm
    template_name = 'desk_callout_create.html'
    permission_required = 'main.desk'

    def get_form(self):
        form = super().get_form()

        form.fields['operation_type'].choices = [
            c for c in form.fields['operation_type'].choices
            if c[0] != 'information']

        form.fields['title'].label = "Title (short description)"
        form.fields['description'].label = "Description with additional details"
        form.fields['description'].widget.attrs = { 'rows':4 }
        form.fields['location'].label = 'Incident Location (Physical description, e.g. "Rock Pool", "S/O tunnel 3")'
        form.fields['lat'].label = 'Incident Coordinates Lat. (Example: 34.137018)'
        form.fields['lon'].label = 'Incident Coordinates Long. (Example: -118.714410)'

        form.fields['radio_channel'].label = "Tactical Channel (Example: LHS-Metro)"
        form.fields['handling_unit'].label = "Tag / Handling Unit"
        form.fields['subject'].label = "DP/Subject"
        form.fields['subject_contact'].label = "DP/Subject Phone Number)"
        form.fields['informant_contact'].label = "Informant Phone Number"

        return form

    def form_valid(self, form):
        object = form.save(commit=False)
        if not object.type:
            object.type = 'operation'
        if object.start_at is None:
            object.start_at = timezone.now()
        if object.status is None:
            object.status = 'active'
        if object.created_by is None:
            object.created_by = self.request.user
        object.save()
        self.object = object
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('desk_callout_detail', args=[self.object.id])

class DeskCalloutCreateView(DeskCalloutBaseView, generic.edit.CreateView):
    pass

class DeskCalloutUpdateView(DeskCalloutBaseView, generic.edit.UpdateView):
    pass

class DeskCalloutDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Event
    template_name = 'desk_callout_detail.html'
    permission_required = 'main.desk'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'calloutlog_set',
            'calloutlog_set__member',
        )

class DeskCalloutListView(PermissionRequiredMixin, generic.ListView):
    model = Event
    template_name = 'desk_callout_list.html'
    context_object_name = 'callout_list'
    permission_required = 'main.desk'

    def get_queryset(self):
        return (Event.objects
                .filter(type='operation',status='active')
                .exclude(operation_type='information')
                .order_by('-id'))
