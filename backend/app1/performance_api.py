"""
Performance Monitoring API Endpoints
====================================

REST API endpoints for real-time performance metrics and optimization monitoring.

Endpoints:
- /api/performance/metrics/         - Real-time performance stats
- /api/performance/optimization/    - Optimization status
- /api/performance/cache-stats/     - Caching statistics
- /api/performance/thread-status/   - Thread health status
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import datetime
import psutil

# Import optimization modules
from .performance_optimizer import get_optimizer
from .db_optimization import get_db_optimizer
from .behavior_thread_optimized import get_analysis_thread, get_performance_stats, get_optimization_status


class PerformanceMonitoringViewSet(viewsets.ViewSet):
    """
    Real-time performance monitoring API.
    
    Provides detailed metrics about system performance, optimization
    strategies, caching effectiveness, and thread health.
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        Get current real-time performance metrics.
        
        Returns:
        --------
        {
            'system': {...},        # System-level metrics
            'optimizer': {...},     # Optimization metrics
            'database': {...},      # Database metrics
            'thread': {...},        # Thread health
            'timestamp': iso string
        }
        """
        try:
            optimizer = get_optimizer()
            db_optimizer = get_db_optimizer()
            thread = get_analysis_thread()
            
            # System metrics
            process = psutil.Process()
            system_metrics = {
                'cpu_percent': round(psutil.cpu_percent(interval=0.1), 2),
                'memory_percent': round(psutil.virtual_memory().percent, 2),
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                'process_cpu': round(process.cpu_percent(interval=0.1), 2),
            }
            
            # Optimizer metrics
            optimizer_metrics = optimizer.get_full_metrics()
            
            # Database metrics
            cache_stats = db_optimizer.get_cache_stats()
            
            # Thread metrics
            thread_metrics = None
            if thread:
                thread_metrics = {
                    'is_running': thread.is_running,
                    'frames_submitted': thread.frame_count,
                    'frames_processed': thread.processed_frames,
                    'frames_skipped': thread.skipped_frames,
                    'current_fps': thread.last_fps,
                    'queue_size': thread.frame_queue.qsize(),
                }
            
            response = {
                'system': system_metrics,
                'optimizer': optimizer_metrics,
                'database': cache_stats,
                'thread': thread_metrics,
                'timestamp': datetime.now().isoformat(),
            }
            
            return Response(response)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def optimization(self, request):
        """
        Get optimization status and recommendations.
        
        Returns:
        --------
        {
            'enabled': bool,
            'components': {...},    # Status of each optimization component
            'recommendations': [...], # Actionable recommendations
            'status': 'healthy|warning|critical'
        }
        """
        try:
            optimizer = get_optimizer()
            metrics = optimizer.get_full_metrics()
            perf = metrics['performance']
            
            # Determine overall status
            status_level = 'healthy'
            recommendations = []
            
            if perf['cpu_percent'] > 85:
                status_level = 'critical'
                recommendations.append({
                    'level': 'critical',
                    'message': 'CPU critically high - increase frame skipping'
                })
            elif perf['cpu_percent'] > 75:
                status_level = 'warning'
                recommendations.append({
                    'level': 'warning',
                    'message': 'CPU usage elevated - monitor frame queue'
                })
            
            if perf['queue_size'] > 20:
                if status_level == 'healthy':
                    status_level = 'warning'
                recommendations.append({
                    'level': 'warning',
                    'message': 'Frame queue backing up - processing falling behind'
                })
            
            if perf['fps'] < 15:
                if status_level == 'healthy':
                    status_level = 'warning'
                recommendations.append({
                    'level': 'warning',
                    'message': 'FPS below 15 - consider reducing resolution'
                })
            
            response = {
                'enabled': True,
                'status': status_level,
                'components': {
                    'frame_skipping': {
                        'enabled': True,
                        'skip_rate': metrics['frame_skipping']['skip_rate'],
                        'process_ratio': metrics['frame_skipping']['process_ratio'],
                    },
                    'resolution_adaptation': {
                        'enabled': True,
                        'current_resolution': metrics['resolution']['current_resolution'],
                        'scale_factor': metrics['resolution']['scale_factor'],
                    },
                    'memory_pooling': {
                        'enabled': True,
                        'pool_size': metrics['memory_pool']['pool_size'],
                        'in_use': metrics['memory_pool']['in_use'],
                        'available': metrics['memory_pool']['available'],
                    },
                    'cpu_throttling': {
                        'enabled': True,
                        'throttle_events': metrics['cpu_throttle']['throttle_events'],
                        'target_fps': metrics['cpu_throttle']['target_fps'],
                    }
                },
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat(),
            }
            
            return Response(response)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def cache_stats(self, request):
        """
        Get database caching statistics.
        
        Returns:
        --------
        {
            'hits': int,
            'misses': int,
            'hit_rate': float,
            'cached_items': int,
            'query_count': int,
            'avg_query_time': float
        }
        """
        try:
            db_optimizer = get_db_optimizer()
            stats = db_optimizer.get_cache_stats()
            
            response = {
                **stats['cache_stats'],
                'query_count': stats['total_queries'],
                'avg_query_time_ms': round(stats['avg_query_time'] * 1000, 2),
                'total_time_ms': round(stats['total_time'] * 1000, 2),
                'timestamp': datetime.now().isoformat(),
            }
            
            return Response(response)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def thread_status(self, request):
        """
        Get behavior analysis thread health status.
        
        Returns:
        --------
        {
            'is_running': bool,
            'frames_processed': int,
            'queue_size': int,
            'current_fps': float,
            'health': 'healthy|degraded|critical'
        }
        """
        try:
            thread = get_analysis_thread()
            
            if not thread:
                return Response({
                    'is_running': False,
                    'error': 'Analysis thread not initialized'
                })
            
            queue_size = thread.frame_queue.qsize()
            fps = thread.last_fps
            
            # Determine health
            health = 'healthy'
            if fps < 10 or queue_size > 25:
                health = 'critical'
            elif fps < 15 or queue_size > 20:
                health = 'degraded'
            
            response = {
                'is_running': thread.is_running,
                'frames_submitted': thread.frame_count,
                'frames_processed': thread.processed_frames,
                'frames_skipped': thread.skipped_frames,
                'current_fps': round(fps, 2),
                'queue_size': queue_size,
                'max_queue_size': thread.max_queue_size,
                'health': health,
                'timestamp': datetime.now().isoformat(),
            }
            
            return Response(response)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get comprehensive performance summary.
        
        Returns all metrics in a single convenient response.
        """
        try:
            optimizer = get_optimizer()
            metrics = optimizer.get_full_metrics()
            thread = get_analysis_thread()
            db_optimizer = get_db_optimizer()
            
            response = {
                'performance_summary': {
                    'fps': metrics['performance']['fps'],
                    'cpu_percent': metrics['performance']['cpu_percent'],
                    'memory_percent': metrics['performance']['memory_percent'],
                    'health_status': self._calculate_health_status(metrics, thread, db_optimizer),
                },
                'optimization_active': {
                    'frame_skip_rate': metrics['frame_skipping']['skip_rate'],
                    'resolution': metrics['resolution']['current_resolution'],
                    'memory_pool_utilization': round(
                        100 * metrics['memory_pool']['in_use'] / metrics['memory_pool']['pool_size'], 1
                    ),
                },
                'processing': {
                    'queue_size': metrics['performance']['queue_size'],
                    'frame_count': metrics['performance']['total_frames'],
                    'process_ratio': metrics['frame_skipping']['process_ratio'],
                },
                'caching': {
                    'hit_rate': db_optimizer.get_cache_stats()['cache_stats']['hit_rate'],
                    'cached_items': db_optimizer.get_cache_stats()['cache_stats']['cached_items'],
                },
                'timestamp': datetime.now().isoformat(),
            }
            
            return Response(response)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @staticmethod
    def _calculate_health_status(metrics, thread, db_optimizer) -> str:
        """Calculate overall health status."""
        perf = metrics['performance']
        
        if perf['cpu_percent'] > 85 or (thread and thread.last_fps < 10):
            return 'critical'
        elif perf['cpu_percent'] > 75 or (thread and thread.last_fps < 15):
            return 'degraded'
        else:
            return 'healthy'


# URL configuration for this viewset
# Add to your main urls.py:
#
# from rest_framework.routers import DefaultRouter
# from .performance_api import PerformanceMonitoringViewSet
#
# router = DefaultRouter()
# router.register(r'performance', PerformanceMonitoringViewSet, basename='performance')
# urlpatterns = [..., path('api/', include(router.urls))]
#
# Then access:
# GET /api/performance/metrics/
# GET /api/performance/optimization/
# GET /api/performance/cache_stats/
# GET /api/performance/thread_status/
# GET /api/performance/summary/
