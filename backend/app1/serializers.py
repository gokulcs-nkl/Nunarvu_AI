from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Attendance, CameraConfiguration, ClassroomObjectDetection


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']


class StudentSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = ['id', 'name', 'email', 'phone_number', 'student_class', 'image', 'image_url', 'authorized']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_class = serializers.CharField(source='student.student_class', read_only=True)
    
    class Meta:
        model = Attendance
        fields = ['id', 'student', 'student_name', 'student_email', 'student_class', 
                 'check_in_time', 'check_out_time', 'date']


class CameraConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraConfiguration
        fields = ['id', 'name', 'camera_source', 'threshold']


class ClassroomObjectDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassroomObjectDetection
        fields = ['id', 'object_type', 'confidence_score', 'image_snapshot', 'date_detected', 'camera_configuration', 'notes']


# Authentication Serializers
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    

class StudentCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    
    class Meta:
        model = Student
        fields = ['name', 'email', 'phone_number', 'student_class', 'image']


class FaceRecognitionSerializer(serializers.Serializer):
    """Serializer for face recognition API"""
    image = serializers.ImageField(help_text="Image containing faces to recognize")
    camera_source = serializers.CharField(required=False, help_text="Camera source identifier")
    
    
class AttendanceStatsSerializer(serializers.Serializer):
    """Serializer for attendance statistics"""
    total_students = serializers.IntegerField()
    total_attendance_records = serializers.IntegerField()
    present_today = serializers.IntegerField()
    absent_today = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    class_wise_stats = serializers.DictField()
    recent_attendance = AttendanceSerializer(many=True, read_only=True)