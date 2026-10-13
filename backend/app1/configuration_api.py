"""
Configuration API Endpoints
===========================

REST API for managing behavior analysis system configurations.

Endpoints:
- /api/config/behavior/       - System configuration
- /api/config/optimization/   - Optimization settings
- /api/config/detectors/      - Detector configurations
- /api/config/thresholds/     - Alert thresholds
- /api/config/audit/          - Audit trail
- /api/config/presets/        - Configuration presets
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q, Count
from .configuration_models import (
    BehaviorConfig, OptimizationConfig, DetectorConfig,
    ThresholdConfig, ConfigurationAudit,
    get_behavior_config, get_optimization_config, get_threshold_config
)


# Serializers
class BehaviorConfigSerializer(ModelSerializer):
    class Meta:
        model = BehaviorConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by')


class OptimizationConfigSerializer(ModelSerializer):
    class Meta:
        model = OptimizationConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by')


class DetectorConfigSerializer(ModelSerializer):
    class Meta:
        model = DetectorConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by')


class ThresholdConfigSerializer(ModelSerializer):
    class Meta:
        model = ThresholdConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by')


class ConfigurationAuditSerializer(ModelSerializer):
    class Meta:
        model = ConfigurationAudit
        fields = '__all__'
        read_only_fields = [field.name for field in ConfigurationAudit._meta.fields]


# ViewSets
class BehaviorConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint for system behavior configuration.
    
    Manage global settings for behavior analysis system.
    """
    
    queryset = BehaviorConfig.objects.all()
    serializer_class = BehaviorConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current behavior configuration."""
        config = get_behavior_config()
        serializer = BehaviorConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_current(self, request):
        """Update current behavior configuration."""
        config = get_behavior_config()
        serializer = BehaviorConfigSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            
            # Log audit trail
            for field, value in request.data.items():
                if field != 'updated_by':
                    ConfigurationAudit.objects.create(
                        config_type='system',
                        changed_by=request.user,
                        changed_field=field,
                        new_value=str(value),
                        reason=request.data.get('reason', 'Updated via API')
                    )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def options(self, request):
        """Get available configuration options."""
        return Response({
            'processing_modes': [
                {'value': 'realtime', 'label': 'Real-time'},
                {'value': 'batch', 'label': 'Batch Processing'},
                {'value': 'hybrid', 'label': 'Hybrid'},
            ],
            'log_levels': [
                {'value': 'DEBUG', 'label': 'Debug'},
                {'value': 'INFO', 'label': 'Info'},
                {'value': 'WARNING', 'label': 'Warning'},
                {'value': 'ERROR', 'label': 'Error'},
            ],
        })


class OptimizationConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint for performance optimization configuration.
    
    Manage frame skipping, resolution adaptation, memory pooling,
    and CPU throttling parameters.
    """
    
    queryset = OptimizationConfig.objects.all()
    serializer_class = OptimizationConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current optimization configuration."""
        config = get_optimization_config()
        serializer = OptimizationConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_current(self, request):
        """Update optimization configuration."""
        config = get_optimization_config()
        serializer = OptimizationConfigSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            
            # Log audit trail
            for field, value in request.data.items():
                if field != 'updated_by':
                    ConfigurationAudit.objects.create(
                        config_type='optimization',
                        changed_by=request.user,
                        changed_field=field,
                        new_value=str(value),
                        reason=request.data.get('reason', 'Updated via API')
                    )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def presets(self, request):
        """Get optimization presets (conservative, balanced, aggressive)."""
        return Response({
            'conservative': {
                'name': 'Conservative',
                'description': 'Minimal optimization - process most frames',
                'settings': {
                    'frame_skip_enabled': True,
                    'initial_skip_rate': 1,
                    'resolution_adapt_enabled': False,
                    'cpu_throttle_enabled': False,
                    'cache_enabled': True,
                }
            },
            'balanced': {
                'name': 'Balanced (Default)',
                'description': 'Automatic optimization with adaptive strategies',
                'settings': {
                    'frame_skip_enabled': True,
                    'initial_skip_rate': 1,
                    'resolution_adapt_enabled': True,
                    'cpu_throttle_enabled': True,
                    'cache_enabled': True,
                }
            },
            'aggressive': {
                'name': 'Aggressive',
                'description': 'Maximum optimization - reduced processing load',
                'settings': {
                    'frame_skip_enabled': True,
                    'initial_skip_rate': 3,
                    'resolution_adapt_enabled': True,
                    'cpu_threshold_high': 75.0,
                    'cpu_throttle_enabled': True,
                    'cache_enabled': True,
                    'memory_pool_size': 20,
                }
            },
        })
    
    @action(detail=False, methods=['post'])
    def apply_preset(self, request):
        """Apply an optimization preset."""
        preset_name = request.data.get('preset')
        
        presets = {
            'conservative': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 1,
                'max_skip_rate': 2,
                'resolution_adapt_enabled': False,
                'cpu_throttle_enabled': False,
            },
            'balanced': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 1,
                'max_skip_rate': 5,
                'resolution_adapt_enabled': True,
                'cpu_throttle_enabled': True,
            },
            'aggressive': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 2,
                'max_skip_rate': 5,
                'resolution_adapt_enabled': True,
                'cpu_threshold_high': 70.0,
                'cpu_throttle_enabled': True,
                'memory_pool_size': 20,
            },
        }
        
        if preset_name not in presets:
            return Response(
                {'error': f'Unknown preset: {preset_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        config = get_optimization_config()
        settings = presets[preset_name]
        
        for field, value in settings.items():
            setattr(config, field, value)
        
        config.updated_by = request.user
        config.save()
        
        # Log audit
        ConfigurationAudit.objects.create(
            config_type='optimization',
            changed_by=request.user,
            changed_field='preset_applied',
            new_value=preset_name,
            reason=f'Applied {preset_name} preset'
        )
        
        serializer = OptimizationConfigSerializer(config)
        return Response(serializer.data)


class DetectorConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint for detector configurations.
    
    Manage parameters for individual behavior detectors.
    """
    
    queryset = DetectorConfig.objects.all()
    serializer_class = DetectorConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def list_detectors(self, request):
        """List all detector configurations."""
        configs = DetectorConfig.objects.all()
        serializer = DetectorConfigSerializer(configs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def get_detector(self, request):
        """Get configuration for a specific detector."""
        detector_type = request.query_params.get('type')
        
        if not detector_type:
            return Response(
                {'error': 'detector type required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            config = DetectorConfig.objects.get(detector_type=detector_type)
            serializer = DetectorConfigSerializer(config)
            return Response(serializer.data)
        except DetectorConfig.DoesNotExist:
            return Response(
                {'error': 'detector not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['put', 'patch'])
    def update_detector(self, request):
        """Update detector configuration."""
        detector_type = request.data.get('detector_type')
        
        if not detector_type:
            return Response(
                {'error': 'detector_type required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            config = DetectorConfig.objects.get(detector_type=detector_type)
        except DetectorConfig.DoesNotExist:
            config = DetectorConfig(detector_type=detector_type)
        
        serializer = DetectorConfigSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            
            # Log audit trail
            for field, value in request.data.items():
                if field not in ['detector_type', 'updated_by']:
                    ConfigurationAudit.objects.create(
                        config_type='detector',
                        changed_by=request.user,
                        changed_field=f'{detector_type}.{field}',
                        new_value=str(value),
                        reason=request.data.get('reason', 'Updated via API')
                    )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ThresholdConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint for alert thresholds.
    
    Configure scoring thresholds for attention levels and
    component-specific alerts.
    """
    
    queryset = ThresholdConfig.objects.all()
    serializer_class = ThresholdConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current threshold configuration."""
        config = get_threshold_config()
        serializer = ThresholdConfigSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_current(self, request):
        """Update threshold configuration."""
        config = get_threshold_config()
        serializer = ThresholdConfigSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            
            # Log audit trail
            for field, value in request.data.items():
                if field != 'updated_by':
                    ConfigurationAudit.objects.create(
                        config_type='threshold',
                        changed_by=request.user,
                        changed_field=field,
                        new_value=str(value),
                        reason=request.data.get('reason', 'Updated via API')
                    )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfigurationAuditViewSet(viewsets.ModelViewSet):
    """
    API endpoint for configuration audit trail.
    
    View all configuration changes for compliance and debugging.
    """
    
    queryset = ConfigurationAudit.objects.all().order_by('-created_at')
    serializer_class = ConfigurationAuditSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'head', 'options']  # Read-only
    
    @action(detail=False, methods=['get'])
    def list_audits(self, request):
        """List configuration audits with filtering."""
        queryset = ConfigurationAudit.objects.all()
        
        # Filter by config type
        config_type = request.query_params.get('type')
        if config_type:
            queryset = queryset.filter(config_type=config_type)
        
        # Filter by changed_by user
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(changed_by_id=user_id)
        
        # Limit results
        limit = int(request.query_params.get('limit', 100))
        queryset = queryset[:limit]
        
        serializer = ConfigurationAuditSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit statistics."""
        total_changes = ConfigurationAudit.objects.count()
        changes_by_type = ConfigurationAudit.objects.values('config_type').annotate(count=Count('id'))
        changes_by_user = ConfigurationAudit.objects.values('changed_by__username').annotate(count=Count('id'))
        
        return Response({
            'total_changes': total_changes,
            'by_type': list(changes_by_type),
            'by_user': list(changes_by_user),
        })


# URL configuration
# Add to api_urls.py:
#
# from .configuration_api import (
#     BehaviorConfigViewSet, OptimizationConfigViewSet,
#     DetectorConfigViewSet, ThresholdConfigViewSet,
#     ConfigurationAuditViewSet
# )
# from rest_framework.routers import DefaultRouter
#
# router = DefaultRouter()
# router.register(r'config/behavior', BehaviorConfigViewSet, basename='behavior-config')
# router.register(r'config/optimization', OptimizationConfigViewSet, basename='optimization-config')
# router.register(r'config/detectors', DetectorConfigViewSet, basename='detector-config')
# router.register(r'config/thresholds', ThresholdConfigViewSet, basename='threshold-config')
# router.register(r'config/audit', ConfigurationAuditViewSet, basename='config-audit')
#
# urlpatterns = [..., path('', include(router.urls))]
