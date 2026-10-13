"""
Configuration Views - Web Interface
===================================

Django views for configuration management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from .configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig,
    ThresholdConfig, ConfigurationAudit,
    get_behavior_config, get_optimization_config, get_threshold_config
)
from .configuration_forms import (
    BehaviorConfigForm, OptimizationConfigForm,
    DetectorConfigForm, ThresholdConfigForm
)


def is_admin_or_staff(user):
    """Check if user is admin or staff."""
    return user.is_staff or user.is_superuser


class ConfigurationDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Main configuration dashboard."""
    template_name = 'configuration/dashboard.html'
    login_url = 'login'
    
    def test_func(self):
        return is_admin_or_staff(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, 'Permission denied.')
        return redirect('home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['behavior_config'] = get_behavior_config()
            context['optimization_config'] = get_optimization_config()
            context['threshold_config'] = get_threshold_config()
            context['detectors'] = DetectorConfig.objects.all()
            context['recent_audits'] = ConfigurationAudit.objects.all()[:10]
        except Exception as e:
            messages.error(self.request, f'Error: {str(e)}')
        return context


class BehaviorConfigView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Manage behavior configuration."""
    template_name = 'configuration/behavior_config.html'
    form_class = BehaviorConfigForm
    login_url = 'login'
    success_url = reverse_lazy('configuration:behavior')
    
    def test_func(self):
        return is_admin_or_staff(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, 'Permission denied.')
        return redirect('home')
    
    def get_initial(self):
        config = get_behavior_config()
        return {
            'system_enabled': config.system_enabled,
            'processing_mode': config.processing_mode,
            'min_fps': config.min_fps,
            'target_fps': config.target_fps,
        }
    
    def form_valid(self, form):
        config = get_behavior_config()
        for field, value in form.cleaned_data.items():
            setattr(config, field, value)
        config.updated_by = self.request.user
        config.save()
        messages.success(self.request, 'Configuration updated!')
        return super().form_valid(form)


@login_required
def configuration_audit_view(request):
    """View configuration audit trail."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('home')
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit
    
    audits = ConfigurationAudit.objects.all().order_by('-created_at')[offset:offset + limit]
    
    return render(request, 'configuration/audit_trail.html', {
        'audits': audits,
        'page': page,
        'limit': limit,
    })


@login_required
def export_configuration(request):
    """Export configuration as JSON."""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import json
    
    behavior = get_behavior_config()
    optimization = get_optimization_config()
    
    config = {
        'behavior': {
            'system_enabled': behavior.system_enabled,
            'processing_mode': behavior.processing_mode,
            'target_fps': behavior.target_fps,
        },
        'optimization': {
            'frame_skip_enabled': optimization.frame_skip_enabled,
            'initial_skip_rate': optimization.initial_skip_rate,
        },
    }
    
    response = JsonResponse(config)
    response['Content-Disposition'] = 'attachment; filename="config.json"'
    return response
