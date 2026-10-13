"""
Behavior Dashboard URL Configuration
Handles routing for all behavior analysis dashboard pages
"""

from django.urls import path
from .behavior_dashboard_views import (
    BehaviorDashboardView,
    StudentAttentionListView,
    BehaviorAnalyticsView,
)

app_name = 'behavior_dashboard'

urlpatterns = [
    # Main real-time dashboard
    path(
        'behavior-dashboard/',
        BehaviorDashboardView.as_view(),
        name='dashboard'
    ),
    
    # Student attention monitoring list
    path(
        'student-attention/',
        StudentAttentionListView.as_view(),
        name='attention_list'
    ),
    
    # Analytics and reporting
    path(
        'behavior-analytics/',
        BehaviorAnalyticsView.as_view(),
        name='analytics'
    ),
]
