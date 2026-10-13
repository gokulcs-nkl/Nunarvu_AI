"""
Database Query Optimization and Caching Layer
==============================================

Implements caching strategies, query optimization, and lazy loading
to reduce database load and improve API response times.

Features:
- Query result caching with TTL
- Aggregated query execution
- Index hints for common queries
- Lazy loading for related objects
- Cache invalidation strategies
"""

import threading
import time
from functools import wraps
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import QuerySet, Q, Count, Avg, Max
from collections import deque


class CacheConfig:
    """Configuration for caching behavior."""
    
    # Cache durations (in seconds)
    ATTENDANCE_TTL = 300  # 5 minutes
    STUDENT_SCORES_TTL = 60  # 1 minute - real-time data
    ALERTS_TTL = 30  # 30 seconds - very dynamic
    STATISTICS_TTL = 300  # 5 minutes
    CLASSROOM_SESSION_TTL = 600  # 10 minutes
    
    # Cache key patterns
    CACHE_PREFIX = "behav_"
    
    @staticmethod
    def get_cache_key(entity: str, entity_id: Any = None, suffix: str = None) -> str:
        """Generate cache key."""
        parts = [CacheConfig.CACHE_PREFIX, entity]
        if entity_id is not None:
            parts.append(str(entity_id))
        if suffix:
            parts.append(suffix)
        return "_".join(parts)


class QueryCache:
    """
    Thread-safe query result caching system.
    
    Caches query results with configurable TTL and provides
    cache invalidation strategies.
    """
    
    def __init__(self):
        self.cache_data = {}
        self.cache_times = {}
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self.lock:
            if key in self.cache_data:
                cached_time = self.cache_times.get(key, 0)
                if time.time() - cached_time < ttl:
                    self.hits += 1
                    return self.cache_data[key]
            self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """Store value in cache."""
        with self.lock:
            self.cache_data[key] = value
            self.cache_times[key] = time.time()
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern."""
        with self.lock:
            if pattern is None:
                self.cache_data.clear()
                self.cache_times.clear()
            else:
                # Remove entries matching pattern
                keys_to_remove = [k for k in self.cache_data.keys() if pattern in k]
                for k in keys_to_remove:
                    del self.cache_data[k]
                    del self.cache_times[k]
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate': round(hit_rate, 2),
            'cached_items': len(self.cache_data)
        }


class DatabaseOptimizer:
    """
    Optimizes database queries through caching and aggregation.
    
    Provides optimized query methods for common access patterns
    with built-in caching and lazy loading.
    """
    
    def __init__(self):
        self.query_cache = QueryCache()
        self.lock = threading.Lock()
        self.query_count = 0
        self.query_time_total = 0
        self.cache_enabled = True
    
    def cached_query(self, ttl: int = 300):
        """Decorator for caching query results."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = f"query_{func.__name__}_{str(args)}_{str(kwargs)}"
                
                # Check cache
                result = self.query_cache.get(cache_key, ttl)
                if result is not None:
                    return result
                
                # Execute query
                start_time = time.time()
                result = func(*args, **kwargs)
                query_time = time.time() - start_time
                
                # Update statistics
                with self.lock:
                    self.query_count += 1
                    self.query_time_total += query_time
                
                # Cache result
                self.query_cache.set(cache_key, result)
                return result
            
            return wrapper
        return decorator
    
    def get_student_scores_optimized(self, classroom_id: int = None):
        """
        Get student attention scores with optimization.
        
        Returns:
        --------
        list : List of (student_id, name, score, status) tuples
        """
        # Import here to avoid circular imports
        from .models import AttentionScore, Student
        
        cache_key = CacheConfig.get_cache_key('student_scores', classroom_id)
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            # Build query with select_related for performance
            query = Student.objects.select_related('classroom').only(
                'id', 'name', 'enrollment_number', 'classroom_id'
            )
            
            if classroom_id:
                query = query.filter(classroom_id=classroom_id)
            
            # Fetch related scores in single query
            results = []
            student_ids = list(query.values_list('id', flat=True))
            
            scores = AttentionScore.objects.filter(
                student_id__in=student_ids
            ).values('student_id').annotate(
                latest_score=Max('attention_score'),
                latest_time=Max('timestamp')
            )
            
            score_dict = {s['student_id']: s['latest_score'] for s in scores}
            
            for student in query:
                score = score_dict.get(student.id, 0)
                results.append({
                    'student_id': student.id,
                    'name': student.name,
                    'score': score,
                    'status': self._get_status(score)
                })
            
            # Cache result
            cache.set(cache_key, results, CacheConfig.STUDENT_SCORES_TTL)
            return results
        
        except Exception as e:
            print(f"[DatabaseOptimizer] Error fetching student scores: {e}")
            return []
    
    def get_alerts_optimized(self, limit: int = 50, unacknowledged_only: bool = True):
        """
        Get recent alerts with optimization.
        
        Uses indexed queries and caching for fast retrieval.
        """
        from .models import BehaviourAlert
        
        cache_key = CacheConfig.get_cache_key(
            'alerts', 
            suffix=f"{'unack' if unacknowledged_only else 'all'}_{limit}"
        )
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            query = BehaviourAlert.objects.select_related('student').only(
                'id', 'student_id', 'alert_type', 'severity', 'created_at', 
                'acknowledged', 'student__name'
            )
            
            if unacknowledged_only:
                query = query.filter(acknowledged=False)
            
            alerts = list(query.order_by('-created_at')[:limit].values(
                'id', 'student__name', 'alert_type', 'severity', 'created_at'
            ))
            
            cache.set(cache_key, alerts, CacheConfig.ALERTS_TTL)
            return alerts
        
        except Exception as e:
            print(f"[DatabaseOptimizer] Error fetching alerts: {e}")
            return []
    
    def get_daily_statistics_optimized(self, start_date: datetime = None, end_date: datetime = None):
        """
        Get aggregated daily statistics efficiently.
        
        Uses database aggregation to reduce result size.
        """
        from .models import AttentionScore, BehaviourAlert
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()
        
        cache_key = CacheConfig.get_cache_key(
            'daily_stats',
            suffix=f"{start_date.date()}_{end_date.date()}"
        )
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            # Get daily aggregates
            stats = AttentionScore.objects.filter(
                timestamp__date__range=[start_date.date(), end_date.date()]
            ).extra(
                select={'day': 'DATE(timestamp)'}
            ).values('day').annotate(
                avg_score=Avg('attention_score'),
                count=Count('id')
            )
            
            # Get alert counts by day
            alerts = BehaviourAlert.objects.filter(
                created_at__date__range=[start_date.date(), end_date.date()]
            ).extra(
                select={'day': 'DATE(created_at)'}
            ).values('day').annotate(
                count=Count('id')
            )
            
            alert_dict = {str(a['day']): a['count'] for a in alerts}
            
            result = []
            for stat in stats:
                result.append({
                    'date': str(stat['day']),
                    'avg_score': round(stat['avg_score'], 2) if stat['avg_score'] else 0,
                    'score_count': stat['count'],
                    'alert_count': alert_dict.get(str(stat['day']), 0)
                })
            
            cache.set(cache_key, result, CacheConfig.STATISTICS_TTL)
            return result
        
        except Exception as e:
            print(f"[DatabaseOptimizer] Error fetching daily statistics: {e}")
            return []
    
    def get_student_events_optimized(self, student_id: int, limit: int = 100):
        """
        Get student behavior events efficiently.
        
        Uses indexed queries and filtering for performance.
        """
        from .models import BehaviourEvent
        
        cache_key = CacheConfig.get_cache_key('student_events', student_id, f"_{limit}")
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            events = list(BehaviourEvent.objects.filter(
                student_id=student_id
            ).only(
                'id', 'event_type', 'confidence', 'timestamp', 'duration_seconds'
            ).order_by('-timestamp')[:limit].values())
            
            cache.set(cache_key, events, CacheConfig.STATISTICS_TTL)
            return events
        
        except Exception as e:
            print(f"[DatabaseOptimizer] Error fetching student events: {e}")
            return []
    
    def get_top_students_by_alerts(self, classroom_id: int = None, limit: int = 10):
        """
        Get students with most alerts efficiently.
        
        Uses database aggregation for performance.
        """
        from .models import BehaviourAlert, Student
        
        cache_key = CacheConfig.get_cache_key(
            'top_alerts',
            classroom_id,
            f"_{limit}"
        )
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            query = Student.objects.select_related('classroom')
            
            if classroom_id:
                query = query.filter(classroom_id=classroom_id)
            
            query = query.annotate(
                alert_count=Count('behaviouralert')
            ).order_by('-alert_count')[:limit]
            
            result = list(query.values(
                'id', 'name', 'alert_count'
            ))
            
            cache.set(cache_key, result, CacheConfig.STATISTICS_TTL)
            return result
        
        except Exception as e:
            print(f"[DatabaseOptimizer] Error fetching top students: {e}")
            return []
    
    def invalidate_student_cache(self, student_id: int):
        """Invalidate cache for specific student."""
        pattern = f"student_{student_id}"
        self.query_cache.invalidate(pattern)
        cache.delete_many([
            CacheConfig.get_cache_key('student_scores', None),
            CacheConfig.get_cache_key('student_events', student_id),
        ])
    
    def invalidate_classroom_cache(self, classroom_id: int):
        """Invalidate cache for specific classroom."""
        pattern = f"classroom_{classroom_id}"
        self.query_cache.invalidate(pattern)
        cache.delete(CacheConfig.get_cache_key('student_scores', classroom_id))
    
    def invalidate_all_cache(self):
        """Invalidate all behavior-related caches."""
        self.query_cache.invalidate()
        pattern = f"{CacheConfig.CACHE_PREFIX}*"
        cache.delete_many([CacheConfig.get_cache_key('student_scores', None)])
    
    def get_cache_stats(self) -> Dict:
        """Get caching statistics."""
        stats = self.query_cache.get_stats()
        avg_query_time = self.query_time_total / max(1, self.query_count)
        
        return {
            'cache_stats': stats,
            'total_queries': self.query_count,
            'avg_query_time': round(avg_query_time, 4),
            'total_time': round(self.query_time_total, 2)
        }
    
    def enable_cache(self):
        """Enable caching functionality."""
        self.cache_enabled = True
    
    def disable_cache(self):
        """Disable caching functionality."""
        self.cache_enabled = False
        self.invalidate_all_cache()
    
    @staticmethod
    def _get_status(score: float) -> str:
        """Map score to status string."""
        if score >= 85:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 55:
            return 'fair'
        elif score >= 40:
            return 'poor'
        else:
            return 'critical'


# Global optimizer instance
_db_optimizer = None
_db_optimizer_lock = threading.Lock()


def get_db_optimizer() -> DatabaseOptimizer:
    """Get or create global database optimizer instance."""
    global _db_optimizer
    if _db_optimizer is None:
        with _db_optimizer_lock:
            if _db_optimizer is None:
                _db_optimizer = DatabaseOptimizer()
    return _db_optimizer
