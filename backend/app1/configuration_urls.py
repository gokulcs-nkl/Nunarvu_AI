"""
Configuration URLs
==================

URL patterns for configuration management.
"""

from django.urls import path
from .configuration_views import (
    ConfigurationDashboardView,
    BehaviorConfigView,
    configuration_audit_view,
    export_configuration,
)

app_name = 'configuration'

urlpatterns = [
    path('', ConfigurationDashboardView.as_view(), name='dashboard'),
    path('behavior/', BehaviorConfigView.as_view(), name='behavior'),
    path('audit/', configuration_audit_view, name='audit'),
    path('export/', export_configuration, name='export'),
]
