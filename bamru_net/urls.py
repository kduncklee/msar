"""
    bamru_net URL Configuration

    The `urlpatterns` list routes URLs to views. For more information please see:
        https://docs.djangoproject.com/en/2.0/topics/http/urls/
    Examples:
    Function views
        1. Add an import:  from my_app import views
        2. Add a URL to urlpatterns:  path('', views.home, name='home')
    Class-based views
        1. Add an import:  from other_app.views import Home
        2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
    Including another URLconf
        1. Import the include() function: from django.urls import include, path
        2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from main import views

import rest_framework.authtoken.views
#from rest_framework import routers
from rest_framework.documentation import include_docs_urls
from rest_framework_extensions import routers

router = routers.ExtendedDefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'periods', views.PeriodViewSet)
router.register(r'participants', views.ParticipantViewSet)
router.register(r'patrols', views.PatrolViewSet)
router.register(r'member_status_types', views.MemberStatusTypeViewSet)
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'member_certs', views.MemberCertViewSet, basename='member-cert')
router.register(r'certs', views.CertViewSet)
router.register(r'availability', views.ApiUnavailableViewSet, basename='member-unavailable')
router.register(r'do', views.DoViewSet, basename='do')
router.register(r'member_availability', views.MemberUnavailableViewSet, basename='member-availability')
router.register(r'photos', views.MemberPhotoViewSet)
router.register(r'files', views.DataFileViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'inbound_sms', views.InboundSmsViewSet)
router.register(r'event_notifications', views.EventNotificationsAvailableViewSet, basename='event_notification')
router.register(r'radio_channels', views.RadioChannelsAvailableViewSet, basename='radio_channel')
router.register(r'operation_types', views.OperationTypesAvailableViewSet, basename='operation_type')
router.register(r'callout_responses', views.CalloutResponseOptionViewSet, basename='callout_response')
callouts_router = router.register(r'callouts', views.CalloutViewSet, basename='callout')
callouts_router.register(r'log', views.CalloutLogViewSet, basename='callout-log', parents_query_lookups=['event'])
router.register(r'announcement/log', views.AnnouncementLogViewSet, basename='announcemnt-log')
router.register('devices', views.FCMDeviceAuthorizedViewSet)


urlpatterns = [
    path('', views.IndexView.as_view(), name='home'),

    path('event/', views.EventListView.as_view(), name='event_list'),
    path('event/published/', views.EventPublishedListView.as_view()),
    path('event/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('event/add/', views.EventCreateView.as_view(), name='event_add'),
    path('event/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('event/<int:pk>/period/add/',
         views.EventPeriodAddView.as_view(), name='event_period_add'),
    path('event/<int:event_id>/messages/', views.MessageEventView.as_view(),
         name='message_event'),
    path('event/calendar/', views.EventCalendarView.as_view(), name='event_calendar'),

    path('event/participant/add/<int:period>/',
         views.PeriodParticipantCreateView.as_view(), name='period_participant_add'),

    path('member/', views.MemberListView.as_view(), name='member_list'),
    path('member/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
    path('member/<int:pk>/history', views.MemberHistoryView.as_view(), name='member_history'),
    path('member/<int:pk>/edit', views.MemberEditView.as_view(), name='member_edit'),
    path('member/<int:pk>/photos', views.MemberPhotoView.as_view(), name='member_photos'),
    path('member/add/', views.MemberAddView.as_view(), name='member_add'),

    path('availability/', views.AvailableListView.as_view(), name='available_list'),
    path('member/<int:pk>/availability/', views.MemberAvailabilityListView.as_view(),
         name='member_availability_list'),

    path('file/', views.FileListView.as_view(), name='file_list'),
    path('file/upload/', views.DataFileFormView.as_view(), name='file_upload'),
    path('file_id/<int:id>/', views.download_data_file_by_id_view, name='file_download'),
    path('file/<path:name>', views.download_data_file_by_name_view), # used by wiki
    path('files/<path:name>', views.download_data_file_by_name_view), # used by wiki

    path('photos/', views.MemberPhotoGalleryView.as_view(), name='member_photo_gallery'),
    path('photos/<int:id>/<str:format>/', views.member_photo_by_id_view, name='member_photo_download'),

    path('cert/', views.CertListView.as_view(), name='cert_list'),
    path('member/<int:pk>/certs/', views.MemberCertListView.as_view(),
         name='member_cert_list'),
    path('member/<int:member>/certs/new/', views.CertCreateView.as_view(),
         name='member_cert_new'),
    path('certs/new/', views.CertBulkCreateMemberView.as_view(),
         name='cert_bulk_new'),
    path('certs/new2/', views.CertBulkCreateView.as_view(),
         name='cert_bulk_new2'),
    path('certs/<int:pk>/edit/',
         views.CertEditView.as_view(), name='cert_edit'),
    path('member/<int:member>/certs/<int:cert>/download/<path:name>',
         views.cert_file_download_view, name='member_cert_download'),
    path('certs/<int:cert>/download/',
         views.cert_file_download_view, name='cert_download'),

    path('do/schedule/', views.DoListView.as_view(), name='do_sched'),
    path('do/availability/<int:pk>', views.DoMemberDetailView.as_view(),
         name='do_availability_list'),
    path('do/plan/', views.DoPlanView.as_view(), name='do_plan'),
    path('do/my_availability/', views.DoMyAvailabilityView.as_view(),
         name='my_availabilty'),
    path('do_ahc_status/', views.DoAhcStatusView.as_view(), name='do_ahc_status'),

    path('message/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('message/<int:pk>/repage/', views.MessageRepageCreateView.as_view(),
         name='message_repage'),
    path('message/', views.MessageListView.as_view(), name='message_list'),
    path('message/inbox/<int:member_id>/', views.MessageInboxView.as_view(),
         name='message_inbox'),
    path('message/add/', views.MessageCreateView.as_view(), name='message_add'),
    path('message/test/', views.MessageTestCreateView.as_view(), name='message_test'),
    path('message/inbound/', views.InboundSmsListView.as_view(), name='inbound_list'),

    path('action/become_do/', views.ActionBecomeDo.as_view(), name='action_become_do'),

    path('desk/callout/', views.DeskCalloutListView.as_view(), name='desk_callout_list'),
    path('desk/callout/add', views.DeskCalloutCreateView.as_view(), name='desk_callout_add'),
    path('desk/callout/<int:pk>/', views.DeskCalloutDetailView.as_view(), name='desk_callout_detail'),
    path('desk/callout/<int:pk>/edit/', views.DeskCalloutUpdateView.as_view(), name='desk_callout_update'),
    
    # Message Webhook and Responses
    path('unauth_rsvp/<slug:token>/<slug:rsvp>/', views.unauth_rsvp, name='unauth_rsvp'),
    path('webhooks/anymail/', include('anymail.urls')),
    path('webhooks/sms_callback/', views.sms_callback, name='sms_callback'),
    path('webhooks/sms/', views.sms, name='sms'),

    re_path(r'^api/', include((router.urls, 'api'))),
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', rest_framework.authtoken.views.obtain_auth_token),

    re_path(r'^api-docs/', include_docs_urls(title='BAMRU API')),

    path('admin/', admin.site.urls),

    re_path(r'^openid/', include('oidc_provider.urls', namespace='oidc_provider')),

    re_path(r'^social/', include('social_django.urls', namespace='social')),

    re_path(r'^accounts/login/$', auth_views.LoginView.as_view(), name='login'),
    re_path(r'^accounts/logout/$', auth_views.LogoutView.as_view(), {'next_page': '/'}, name='logout'),
    
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(),
         name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(),
         name='password_change_done'),

    path('accounts/password_reset/',
         auth_views.PasswordResetView.as_view(form_class=views.PasswordResetForm),
         name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(),
         name='password_reset_complete'),

    path('reports/', views.ReportListView.as_view(), name='reports_list'),
    path('reports/roster/BAMRU-roster.csv', views.ReportRosterCsvView.as_view()),
    path('reports/roster/BAMRU-roster.vcf', views.ReportRosterVcfView.as_view()),
    path('reports/roster/BAMRU-<str:roster_type>', views.ReportRosterView.as_view()),
    path('reports/activity-member/<int:pk>/', views.ReportEventMemberView.as_view(), name='report_activity_member'),
    path('reports/activity-member/me/', views.ReportEventMemberViewSelf.as_view(), name='report_activity_member'),
    path('reports/activity-<str:activity_type>/', views.ReportEventView.as_view(), name='report_activity'),
    path('reports/event/errors/', views.ReportEventErrorsView.as_view(), name='report_event_errors'),
    path('reports/cert/expire/', views.CertExpireView.as_view(), name='report_cert_expire'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
