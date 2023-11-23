from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from main.models import Event

import logging
logger = logging.getLogger(__name__)


class CalloutForm(ModelForm):
    class Meta:
        model = Event
        fields = [
            'operation_type', 'title', 'description',
            'location', 'lat', 'lon',
            'location_address', 'location_city', 'location_state', 'location_zip',
            'subject', 'subject_contact', 'informant', 'informant_contact',
            'radio_channel', 'handling_unit',
            'notifications_made',
        ]

class DeskCalloutBaseView(LoginRequiredMixin, generic.edit.ModelFormMixin):
    model = Event
    form_class = CalloutForm
    template_name = 'desk_callout_create.html'

    def get_form(self):
        form = super().get_form()

        form.fields['operation_type'].choices = [
            c for c in form.fields['operation_type'].choices
            if c[0] != 'information']

        form.fields['title'].label = "Short description"
        form.fields['description'].label = "Description with additional details"
        form.fields['description'].widget.attrs = { 'rows':4 }
        form.fields['radio_channel'].label = "Tactical Channel"
        form.fields['handling_unit'].label = "Tag / Handling Unit"
        form.fields['subject_contact'].label = "Subject contact (phone number)"
        form.fields['informant_contact'].label = "Subject contact (phone number)"

        return form

    def form_valid(self, form):
        object = form.save(commit=False)
        if object.type is None:
            object.type = 'operation'
        if object.start_at is None:
            object.start_at = timezone.now()
        if object.status is None:
            object.status = 'active'
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('desk_callout_detail', args=[self.object.id])

class DeskCalloutCreateView(DeskCalloutBaseView, generic.edit.CreateView):
    pass

class DeskCalloutUpdateView(DeskCalloutBaseView, generic.edit.UpdateView):
    pass

class DeskCalloutDetailView(LoginRequiredMixin, generic.DetailView):
    model = Event
    template_name = 'desk_callout_detail.html'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'calloutlog_set',
            'calloutlog_set__member',
        )

class DeskCalloutListView(LoginRequiredMixin, generic.ListView):
    model = Event
    template_name = 'desk_callout_list.html'
    context_object_name = 'callout_list'

    def get_queryset(self):
        return (Event.objects
                .filter(type='operation',status='active')
                .exclude(operation_type='information')
                .order_by('-id'))
