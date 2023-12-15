from django.http import HttpResponse
from django.template import RequestContext, Template
from django.views.generic.base import TemplateView
from dynamic_preferences.registries import global_preferences_registry
from rules.contrib.views import PermissionRequiredMixin


class IndexView(PermissionRequiredMixin, TemplateView):
    template_name = 'index.html'
    permission_required = 'main'

    def render_to_response(self, context, **response_kwargs):
        global_preferences = global_preferences_registry.manager()
        template = global_preferences['template__index']
        if not template:
            return super().render_to_response(context, **response_kwargs)
        c = RequestContext(self.request, context)
        r = Template(template).render(c)
        return HttpResponse(r)
