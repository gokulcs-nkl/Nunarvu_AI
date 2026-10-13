from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    roll_number = serializers.CharField(source='student.roll_number', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'session', 'student', 'student_name', 'roll_number', 'status', 'source',
            'first_seen_at', 'last_seen_at', 'confidence', 'marked_by', 'note', 'updated_at',
        ]
        read_only_fields = ['source', 'first_seen_at', 'last_seen_at', 'confidence', 'marked_by']
        validators = [
            UniqueTogetherValidator(queryset=AttendanceRecord.objects.all(), fields=['session', 'student'], message='Attendance is already recorded for this student in this session.'),
        ]

    def validate(self, attrs):
        session = attrs.get('session', getattr(self.instance, 'session', None))
        student = attrs.get('student', getattr(self.instance, 'student', None))
        if self.instance is not None and (
            attrs.get('session', session) != self.instance.session or attrs.get('student', student) != self.instance.student
        ):
            raise serializers.ValidationError('Session and student cannot be changed on an existing record.')
        if session and student and not student.class_groups.filter(pk=session.class_group_id).exists():
            raise serializers.ValidationError({'student': 'Student is not enrolled in this class.'})
        return attrs
