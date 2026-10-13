"""
Behavior Analysis API Views
============================

DRF ViewSets for behavior analysis REST API.
Provides endpoints for accessing behavior data, alerts, and analytics.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Avg, Count, Q, Max, Min
from datetime import datetime, timedelta

from .models import (
    StudentSeat, BehaviourEvent, AttentionScore,
    BehaviourAlert, ClassroomSession, Student
)
from .behavior_serializers import (
    StudentSeatSerializer, BehaviourEventSerializer, AttentionScoreSerializer,
    BehaviourAlertSerializer, ClassroomSessionSerializer,
    AttentionSummarySerializer, BehaviorStatsSerializer, AlertSummarySerializer
)


class StudentSeatViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student seat assignments.
    
    Endpoints:
    - GET /api/student-seats/ - List all seats
    - POST /api/student-seats/ - Create new seat assignment
    - GET /api/student-seats/{id}/ - Get specific seat
    - PUT /api/student-seats/{id}/ - Update seat
    - DELETE /api/student-seats/{id}/ - Delete seat
    """
    queryset = StudentSeat.objects.all()
    serializer_class = StudentSeatSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['student__name', 'classroom_name']
    ordering_fields = ['classroom_name', 'seat_number', 'created_at']
    
    def get_queryset(self):
        """Filter seats by classroom if specified"""
        queryset = StudentSeat.objects.all()
        classroom = self.request.query_params.get('classroom_name', None)
        
        if classroom:
            queryset = queryset.filter(classroom_name=classroom)
        
        return queryset.order_by('classroom_name', 'seat_number')


class BehaviourEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for behavior events (read-only, auto-generated).
    
    Endpoints:
    - GET /api/behaviour-events/ - List events with filtering
    - GET /api/behaviour-events/{id}/ - Get specific event
    """
    serializer_class = BehaviourEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['student__name', 'event_type']
    ordering_fields = ['timestamp', 'confidence', 'event_type']
    
    def get_queryset(self):
        """Filter events by student, event_type, and date range"""
        queryset = BehaviourEvent.objects.all()
        
        # Filter by student
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by event type
        event_type = self.request.query_params.get('event_type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by date range
        days = int(self.request.query_params.get('days', 1))
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_date)
        
        return queryset.order_by('-timestamp')


class AttentionScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for attention scores.
    
    Endpoints:
    - GET /api/attention-scores/ - List current/recent attention scores
    - GET /api/attention-scores/{id}/ - Get specific score record
    - GET /api/attention-scores/by_student/{student_id}/ - Get student's scores
    """
    serializer_class = AttentionScoreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp', 'overall_score', 'student']
    
    def get_queryset(self):
        """Get recent attention scores (last 24 hours by default)"""
        hours = int(self.request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)
        
        queryset = AttentionScore.objects.filter(
            timestamp__gte=start_time
        ).order_by('-timestamp')
        
        # Filter by student if specified
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest_scores(self, request):
        """Get latest attention score for each student"""
        # Get latest score for each student
        subquery = AttentionScore.objects.filter(
            student_id=AttentionScore.objects.values('student_id').query
        ).order_by('-timestamp').values('id')[:1]
        
        latest_scores = AttentionScore.objects.filter(
            id__in=subquery
        ).select_related('student').order_by('-overall_score')
        
        serializer = self.get_serializer(latest_scores, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_student(self, request, student_id=None):
        """Get attention scores for a specific student"""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {'error': 'student_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)
        
        scores = AttentionScore.objects.filter(
            student_id=student_id,
            timestamp__gte=start_time
        ).order_by('-timestamp')
        
        serializer = self.get_serializer(scores, many=True)
        return Response(serializer.data)


class BehaviourAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for behavior alerts.
    
    Endpoints:
    - GET /api/behaviour-alerts/ - List alerts with filtering
    - GET /api/behaviour-alerts/{id}/ - Get specific alert
    - PATCH /api/behaviour-alerts/{id}/acknowledge/ - Mark alert as acknowledged
    - GET /api/behaviour-alerts/unacknowledged/ - Get unacknowledged alerts
    """
    serializer_class = BehaviourAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['student__name', 'alert_type', 'severity']
    ordering_fields = ['timestamp', 'severity', 'student']
    http_method_names = ['get', 'patch', 'head', 'options']  # Read-mostly
    
    def get_queryset(self):
        """Filter alerts by student, type, acknowledged status, and date range"""
        queryset = BehaviourAlert.objects.all()
        
        # Filter by student
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type', None)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        # Filter by severity
        severity = self.request.query_params.get('severity', None)
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by acknowledged status
        acknowledged = self.request.query_params.get('acknowledged', None)
        if acknowledged is not None:
            queryset = queryset.filter(
                acknowledged=acknowledged.lower() in ['true', '1', 'yes']
            )
        else:
            # Default: unacknowledged only
            queryset = queryset.filter(acknowledged=False)
        
        # Filter by date range
        days = int(self.request.query_params.get('days', 1))
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_date)
        
        return queryset.order_by('-severity', '-timestamp')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Mark alert as acknowledged"""
        alert = self.get_object()
        acknowledged_by = request.data.get('acknowledged_by', request.user.username)
        
        alert.acknowledge_alert(acknowledged_by=acknowledged_by)
        
        serializer = self.get_serializer(alert)
        return Response(
            {'status': 'alert acknowledged', 'alert': serializer.data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def unacknowledged(self, request):
        """Get all unacknowledged alerts"""
        limit = int(request.query_params.get('limit', 50))
        alerts = BehaviourAlert.objects.filter(
            acknowledged=False
        ).select_related('student').order_by(
            '-severity', '-timestamp'
        )[:limit]
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get alert statistics"""
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)
        
        queryset = BehaviourAlert.objects.filter(timestamp__gte=start_time)
        
        stats = {
            'total_alerts': queryset.count(),
            'unacknowledged': queryset.filter(acknowledged=False).count(),
            'by_severity': {
                'high': queryset.filter(severity='high').count(),
                'medium': queryset.filter(severity='medium').count(),
                'low': queryset.filter(severity='low').count(),
            },
            'by_type': {
                'drowsiness': queryset.filter(alert_type='drowsiness').count(),
                'distraction': queryset.filter(alert_type='distraction').count(),
                'phone_usage': queryset.filter(alert_type='phone_usage').count(),
                'posture': queryset.filter(alert_type='posture').count(),
                'absence': queryset.filter(alert_type='absence').count(),
            },
            'time_period_hours': hours
        }
        
        return Response(stats)


class ClassroomSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for classroom sessions.
    
    Endpoints:
    - GET /api/classroom-sessions/ - List sessions
    - POST /api/classroom-sessions/ - Create new session
    - GET /api/classroom-sessions/{id}/ - Get specific session
    - PATCH /api/classroom-sessions/{id}/mark_ended/ - End session
    """
    queryset = ClassroomSession.objects.all()
    serializer_class = ClassroomSessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['classroom_name']
    ordering_fields = ['date', 'start_time', 'classroom_name']
    
    def get_queryset(self):
        """Filter sessions by date and classroom"""
        queryset = ClassroomSession.objects.all()
        
        classroom = self.request.query_params.get('classroom_name', None)
        if classroom:
            queryset = queryset.filter(classroom_name=classroom)
        
        # By default, show only recent sessions
        days = int(self.request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(date__gte=start_date)
        
        return queryset.order_by('-date', '-start_time')
    
    @action(detail=True, methods=['post'])
    def mark_ended(self, request, pk=None):
        """Mark session as ended"""
        session = self.get_object()
        session.mark_ended()
        
        serializer = self.get_serializer(session)
        return Response(
            {'status': 'session ended', 'session': serializer.data},
            status=status.HTTP_200_OK
        )


class BehaviorStatsViewSet(viewsets.ViewSet):
    """
    ViewSet for aggregated behavior statistics and analytics.
    
    Endpoints:
    - GET /api/behavior-stats/classroom/ - Classroom-level stats
    - GET /api/behavior-stats/student/ - Student-level stats
    - GET /api/behavior-stats/daily/ - Daily trend stats
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def classroom(self, request):
        """Get classroom-level behavior statistics"""
        classroom_name = request.query_params.get('classroom_name')
        hours = int(request.query_params.get('hours', 24))
        
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Filter attention scores
        scores_query = AttentionScore.objects.filter(timestamp__gte=start_time)
        if classroom_name:
            scores_query = scores_query.filter(student__seat_assignment__classroom_name=classroom_name)
        
        # Aggregate stats
        stats = scores_query.aggregate(
            avg_attention=Avg('overall_score'),
            min_attention=Min('overall_score'),
            max_attention=Max('overall_score'),
            unique_students=Count('student', distinct=True),
            drowsy_count=Count('id', filter=Q(is_drowsy=True)),
            distracted_count=Count('id', filter=Q(is_looking_away=True)),
            phone_count=Count('id', filter=Q(is_using_phone=True)),
            bad_posture_count=Count('id', filter=Q(has_bad_posture=True)),
        )
        
        # Alert stats
        alerts_query = BehaviourAlert.objects.filter(timestamp__gte=start_time)
        if classroom_name:
            alerts_query = alerts_query.filter(
                student__seat_assignment__classroom_name=classroom_name
            )
        
        alert_stats = alerts_query.aggregate(
            total_alerts=Count('id'),
            critical_alerts=Count('id', filter=Q(severity='high')),
            unacknowledged=Count('id', filter=Q(acknowledged=False))
        )
        
        result = {
            'classroom_name': classroom_name or 'All Classrooms',
            'period_hours': hours,
            'attention': stats,
            'alerts': alert_stats
        }
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def student(self, request):
        """Get per-student behavior statistics"""
        hours = int(request.query_params.get('hours', 24))
        limit = int(request.query_params.get('limit', 50))
        
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Get latest attention score for each student
        latest_scores = AttentionScore.objects.filter(
            timestamp__gte=start_time
        ).values('student').annotate(
            latest_timestamp=Max('timestamp'),
            avg_score=Avg('overall_score'),
            min_score=Min('overall_score'),
            max_score=Max('overall_score')
        ).order_by('-avg_score')[:limit]
        
        # Enrich with student names and alert counts
        results = []
        for score_data in latest_scores:
            student = Student.objects.get(id=score_data['student'])
            alert_count = BehaviourAlert.objects.filter(
                student_id=student.id,
                timestamp__gte=start_time
            ).count()
            
            results.append({
                'student_id': student.id,
                'student_name': student.name,
                'avg_attention_score': score_data['avg_score'],
                'min_attention_score': score_data['min_score'],
                'max_attention_score': score_data['max_score'],
                'alert_count': alert_count,
                'period_hours': hours
            })
        
        return Response(results)
    
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Get daily trend statistics"""
        days = int(request.query_params.get('days', 7))
        
        results = []
        for i in range(days):
            date = (timezone.now() - timedelta(days=i)).date()
            
            scores = AttentionScore.objects.filter(
                timestamp__date=date
            ).aggregate(
                avg_score=Avg('overall_score'),
                unique_students=Count('student', distinct=True)
            )
            
            alerts = BehaviourAlert.objects.filter(
                timestamp__date=date
            ).count()
            
            results.append({
                'date': date,
                'avg_attention_score': scores['avg_score'],
                'unique_students': scores['unique_students'],
                'alerts': alerts
            })
        
        return Response(results)
