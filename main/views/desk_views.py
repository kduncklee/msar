from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect
from django.template.defaultfilters import linebreaksbr
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views import generic
from rules.contrib.views import PermissionRequiredMixin

from main.lib import mapping
from main.models import Event, EventNotificationsAvailable, OperationTypesAvailable, RadioChannelsAvailable

import logging
logger = logging.getLogger(__name__)


MIN_LAT = 32
MAX_LAT = 42
MIN_LON = -125
MAX_LON = -114
LAT_LON_STEP = 0.0000001

class CalloutForm(ModelForm):
    class Meta:
        model = Event
        fields = [
            'handling_unit',
            'operation_type',
            'title',
            'location', 'lat', 'lon',
            'location_address', 'location_city',
            'informant', 'informant_contact',
            'description',
            'subject', 'subject_contact',
            'radio_channel', 'additional_radio_channels',
            'notifications_made',
        ]
        widgets = {
            'lat': forms.NumberInput(
                attrs={'min': MIN_LAT, 'max': MAX_LAT,
                       'step': LAT_LON_STEP}),
            'lon': forms.NumberInput(
                attrs={'min': MIN_LON, 'max': MAX_LON,
                       'step': LAT_LON_STEP}),
            'radio_channel': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operation_type'].required = True

    def clean_lat(self):
        lat = self.cleaned_data["lat"]
        if lat:
            try:
                lat = float(lat)
            except:
                raise ValidationError("Invalid Latitude")
            if not MIN_LAT < lat < MAX_LAT:
                raise ValidationError(
                    "Latitude is outside bounds ({} - {})".format(
                        MIN_LAT, MAX_LAT))
        return lat

    def clean_lon(self):
        lon = self.cleaned_data["lon"]
        if lon:
            try:
                lon = float(lon)
            except:
                raise ValidationError("Invalid Longitude")
            if not MIN_LON < lon < MAX_LON:
                raise ValidationError(
                    "Longitude is outside bounds ({} - {})".format(
                        MIN_LON, MAX_LON))
        return lon

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get("lat")
        lon = cleaned_data.get("lon")
        if bool(lat) ^ bool(lon):
            raise ValidationError("Specify both latitude and longitude (or neither).")

class ConfirmCalloutForm(CalloutForm):
    force = forms.BooleanField(required=True, initial=False)
    field_order = ['force']

    def clean_force(self):
        data = self.cleaned_data['force']
        if data:
            logger.info('Force bypassing duplicate callout protection')
            return data
        else:
            raise forms.ValidationError('Please confirm that this is not a duplicate callout.')


class DeskCalloutBaseView(PermissionRequiredMixin, generic.edit.ModelFormMixin):
    model = Event
    form_class = CalloutForm
    template_name = 'desk_callout_create.html'
    permission_required = 'main.desk'

    def get_form(self):
        form = super().get_form()

        form.fields['operation_type'].queryset = OperationTypesAvailable.objects.filter(enabled=True)

        form.fields['handling_unit'].label = "Tag & Handling Unit"
        form.fields['handling_unit'].help_text = "Tag Number and Handling Unit"
        form.fields['handling_unit'].widget.attrs['placeholder'] = ''

        form.fields['title'].label = "Incident Name or Radio Code"
        form.fields['title'].help_text = 'Short name of incident or radio code (Example, either "Car over the side", "901T")'
        form.fields['title'].widget.attrs['placeholder'] = ''

        form.fields['location'].label = "Incident Location"
        form.fields['location'].help_text = 'Physical description of location, Example: "Rock Pool", "S/O tunnel 3")'
        form.fields['location'].widget.attrs['placeholder'] = ''

        form.fields['lat'].label = 'Location Lat'
        form.fields['lat'].help_text = 'Incident Coordinates Latitude (Example: 34.137018)'
        form.fields['lat'].widget.attrs['placeholder'] = ''

        form.fields['lon'].label = 'Location Long'
        form.fields['lon'].help_text = 'Incident Coordinates Longitude. (Example: -118.714410)'
        form.fields['lon'].widget.attrs['placeholder'] = ''

        form.fields['informant'].label = "Informant Name"
        form.fields['informant_contact'].label = "Informant Phone Number"

        form.fields['description'].label = "Details"
        form.fields['description'].help_text = "Description of callout with additional details (Remark)"
        form.fields['description'].widget.attrs = { 'rows':4 }

        form.fields['subject'].label = "DP/Subject Name"
        form.fields['subject'].widget.attrs['placeholder'] = ''

        form.fields['subject_contact'].label = "DP/Subject Phone Number)"
        form.fields['subject_contact'].help_text = "If available"

        form.fields['radio_channel'].label = "Tactical Freq"
        form.fields['radio_channel'].help_text = "Pre-assigned frequency, if needed (Example: LHSMetro)"
        form.fields['radio_channel'].widget.choices=[(None,'')] + [(r.name, r.name) for r in
                         RadioChannelsAvailable.objects.filter(is_primary=True)]

        form.fields['additional_radio_channels'].label = "Additional Radio Channels"
        form.fields['additional_radio_channels'].help_text = "Additional frequencies used (like Fire)"
        form.fields['additional_radio_channels'].queryset = RadioChannelsAvailable.objects.filter(is_additional=True)

        form.fields['notifications_made'].label = "Notifications Made"
        form.fields['notifications_made'].help_text = "List of other agencies already notified. Select all that apply"

        if 'force' in form.fields:
            form.fields['force'].label = mark_safe('WARNING: There is already a callout active.<br><br>If the callout you are making matches the one below, please click it and add any additional information there.<br><br>If this is a new and different call, check this box and fill out the form.')
            form.fields['force'].help_text = format_html(
                '<dl>{}</dl>',
                format_html_join('\n','<dt><a href="{}">{}</a></dt><dd>{}</dd>',
                                 ((reverse('desk_callout_detail', args=[c.id]),
                                   c.title,
                                   linebreaksbr(c.description))
                                  for c in self.recent))
            )

        if self.request.user.status and self.request.user.status.short == 'DESK':
            form.fields['operation_type'].initial = form.fields['operation_type'].queryset.first()  # just default to the first one if one is not selected by the desk
            form.fields['notifications_made'].initial = (
                EventNotificationsAvailable.objects.filter(name='LHS Desk'))

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
        if object.location_address and not object.lat:
            address = object.location_address
            if object.location_city:
                address += ', {}'.format(object.location_city)
            bounds = 'bounds={},{}|{},{}'.format(MIN_LAT,MIN_LON,MAX_LAT,MAX_LON)
            coordinates = mapping.geocode(address, bounds)
            if coordinates:
                (object.lat, object.lon) = coordinates
        object.save()
        form.save_m2m()
        self.object = object
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('desk_callout_detail', args=[self.object.id])

class DeskCalloutCreateView(DeskCalloutBaseView, generic.edit.CreateView):
    def get_form_class(self):
        qs = Event.objects.filter(type='operation', status='active')
        self.recent = qs.filter(created_at__gte=timezone.now() - timedelta(minutes=30))
        return ConfirmCalloutForm if self.recent else CalloutForm

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
        status = self.request.GET.get('status', 'active')
        results = Event.objects.filter(type='operation')
        if status != 'all':
            results = results.filter(status=status)
        return results.order_by('-id')
