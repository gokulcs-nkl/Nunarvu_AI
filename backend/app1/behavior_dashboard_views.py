"""
Behavior Dashboard Views
Handles rendering of behavior analysis dashboard pages
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.conf import settings
import os


class BehaviorDashboardView(LoginRequiredMixin, TemplateView):
    """
    Main real-time behavior analysis dashboard.
    
    Features:
    - Live video stream with student overlays
    - Real-time attention scores
    - Critical alerts
    - System performance metrics
    - Recording and screenshot capabilities
    """
    template_name = 'behavior_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_base_url'] = self.get_api_base_url()
        context['page_title'] = 'Real-Time Classroom Behavior Analysis'
        return context
    
    def get_api_base_url(self):
        """Get the API base URL for AJAX requests"""
        protocol = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host()
        return f'{protocol}://{host}/api'


class StudentAttentionListView(LoginRequiredMixin, TemplateView):
    """
    Real-time student attention monitoring list.
    
    Features:
    - Live student attention scores sorted by concern level
    - Color-coded status indicators
    - Component scores visualization
    - Individual student detail modal
    - Filters by classroom, alert type, time range
    - Search and pagination
    - CSV export capability
    """
    template_name = 'student_attention_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_base_url'] = self.get_api_base_url()
        context['page_title'] = 'Student Attention Monitoring'
        return context
    
    def get_api_base_url(self):
        """Get the API base URL for AJAX requests"""
        protocol = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host()
        return f'{protocol}://{host}/api'


class BehaviorAnalyticsView(LoginRequiredMixin, TemplateView):
    """
    Comprehensive behavior analytics and reporting dashboard.
    
    Features:
    - Time-series charts (attention trends, alert heatmaps)
    - Component analysis (drowsiness, phone usage, posture, etc.)
    - Event log with detailed filtering
    - Alert distribution and timelines
    - Key metrics and statistics
    - Date range filtering
    - Export options (CSV, JSON, PDF)
    - Print-friendly report generation
    """
    template_name = 'behavior_analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_base_url'] = self.get_api_base_url()
        context['page_title'] = 'Behavior Analytics & Reports'
        context['enable_pdf_export'] = self.has_pdf_support()
        return context
    
    def get_api_base_url(self):
        """Get the API base URL for AJAX requests"""
        protocol = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host()
        return f'{protocol}://{host}/api'
    
    def has_pdf_support(self):
        """Check if PDF export is supported"""
        try:
            import pdfkit
            return True
        except ImportError:
            return False
