from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q
from .models import Student, Attendance, CameraConfiguration, ClassroomObjectDetection
from .serializers import (
    StudentSerializer, AttendanceSerializer, CameraConfigurationSerializer,
    ClassroomObjectDetectionSerializer, LoginSerializer, UserSerializer,
    StudentCreateSerializer, FaceRecognitionSerializer, AttendanceStatsSerializer
)
from . import views as template_views


class StudentViewSet(viewsets.ModelViewSet):
    """API ViewSet for Student management"""
    queryset = Student.objects.all().order_by('-id')
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentCreateSerializer
        return StudentSerializer
    
    @action(detail=True, methods=['post'])
    def authorize(self, request, pk=None):
        """Authorize/unauthorize a student"""
        student = self.get_object()
        authorized = request.data.get('authorized', True)
        student.authorized = authorized
        student.save()
        
        serializer = self.get_serializer(student)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get student statistics"""
        total_students = Student.objects.count()
        authorized_students = Student.objects.filter(authorized=True).count()
        class_distribution = Student.objects.values('student_class').annotate(
            count=Count('id')
        ).order_by('student_class')
        
        return Response({
            'total_students': total_students,
            'authorized_students': authorized_students,
            'unauthorized_students': total_students - authorized_students,
            'class_distribution': class_distribution
        })


class AttendanceViewSet(viewsets.ModelViewSet):
    """API ViewSet for Attendance management"""
    queryset = Attendance.objects.all().order_by('-check_in_time')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        student_id = self.request.query_params.get('student_id')
        class_name = self.request.query_params.get('class_name')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if class_name:
            queryset = queryset.filter(student__student_class=class_name)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's attendance"""
        today = timezone.now().date()
        attendance_records = self.get_queryset().filter(date=today)
        serializer = self.get_serializer(attendance_records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get attendance statistics"""
        today = timezone.now().date()
        
        # Total students
        total_students = Student.objects.filter(authorized=True).count()
        
        # Today's attendance
        today_attendance = Attendance.objects.filter(date=today)
        present_today = today_attendance.values('student').distinct().count()
        
        # Recent attendance (last 10 records)
        recent_attendance = Attendance.objects.all().order_by('-check_in_time')[:10]
        
        # Class-wise statistics
        class_stats = Student.objects.values('student_class').annotate(
            total=Count('id'),
            present=Count('attendance', filter=Q(attendance__date=today))
        )
        
        # Calculate attendance rate
        attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0
        
        stats_data = {
            'total_students': total_students,
            'total_attendance_records': Attendance.objects.count(),
            'present_today': present_today,
            'absent_today': total_students - present_today,
            'attendance_rate': round(attendance_rate, 2),
            'class_wise_stats': list(class_stats),
            'recent_attendance': AttendanceSerializer(recent_attendance, many=True, context={'request': request}).data
        }
        
        return Response(stats_data)


class CameraConfigurationViewSet(viewsets.ModelViewSet):
    """API ViewSet for Camera Configuration"""
    queryset = CameraConfiguration.objects.all().order_by('-id')
    serializer_class = CameraConfigurationSerializer
    permission_classes = [IsAuthenticated]


class ClassroomObjectDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for Object Detection Reports"""
    queryset = ClassroomObjectDetection.objects.all().order_by('-date_detected')
    serializer_class = ClassroomObjectDetectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by object type
        object_type = self.request.query_params.get('object_type')
        if object_type:
            queryset = queryset.filter(object_type=object_type)
            
        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """API endpoint for user authentication"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            
            return Response({
                'message': 'Login successful',
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """API endpoint for user logout"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Logout successful'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def face_recognition_api(request):
    """API endpoint for face recognition"""
    serializer = FaceRecognitionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Use existing face recognition logic
            result = template_views.process_face_recognition(request)
            
            if hasattr(result, 'content'):
                # If it's an HttpResponse, extract the data
                import json
                response_data = json.loads(result.content.decode('utf-8'))
                return Response(response_data)
            else:
                return result
        except Exception as e:
            return Response({
                'error': f'Face recognition failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_attendance_api(request):
    """API endpoint for manual attendance marking"""
    student_id = request.data.get('student_id')
    action = request.data.get('action', 'check_in')  # check_in or check_out
    
    if not student_id:
        return Response({
            'error': 'student_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        student = Student.objects.get(id=student_id)
        today = timezone.now().date()
        
        if action == 'check_in':
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                date=today,
                defaults={'check_in_time': timezone.now()}
            )
            
            if not created and attendance.check_in_time:
                return Response({
                    'error': 'Student already checked in today'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            message = f'{student.name} checked in successfully'
        
        elif action == 'check_out':
            try:
                attendance = Attendance.objects.get(student=student, date=today)
                if attendance.check_out_time:
                    return Response({
                        'error': 'Student already checked out today'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                attendance.check_out_time = timezone.now()
                attendance.save()
                message = f'{student.name} checked out successfully'
            
            except Attendance.DoesNotExist:
                return Response({
                    'error': 'No check-in record found for today'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            return Response({
                'error': 'Invalid action. Use check_in or check_out'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get updated attendance record
        attendance = Attendance.objects.get(student=student, date=today)
        serializer = AttendanceSerializer(attendance, context={'request': request})
        
        return Response({
            'message': message,
            'attendance': serializer.data
        })
        
    except Student.DoesNotExist:
        return Response({
            'error': 'Student not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'version': '1.0.0'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_camera(request):
    """Test camera connectivity and capture capabilities"""
    import cv2
    
    camera_source = request.data.get('camera_source', '0')
    threshold = request.data.get('threshold', 0.6)
    
    try:
        # Try to open camera
        if camera_source.isdigit():
            cap = cv2.VideoCapture(int(camera_source))
        else:
            cap = cv2.VideoCapture(camera_source)
        
        # Check if camera opened successfully
        if not cap.isOpened():
            return Response({
                'success': False,
                'error': f'Unable to open camera: {camera_source}. Check camera connection, index, or RTSP URL.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to capture a frame
        ret, frame = cap.read()
        
        if not ret or frame is None:
            cap.release()
            return Response({
                'success': False,
                'error': 'Camera opened but could not capture frame. Try adjusting camera source.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        cap.release()
        
        return Response({
            'success': True,
            'message': 'Camera test successful',
            'camera_source': camera_source,
            'width': width,
            'height': height,
            'fps': fps,
            'threshold': threshold
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error testing camera: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)