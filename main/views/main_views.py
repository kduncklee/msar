from django.views.generic.base import TemplateView
from rules.contrib.views import PermissionRequiredMixin


class IndexView(PermissionRequiredMixin, TemplateView):
    template_name = 'index.html'
    permission_required = 'main'
