from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import (
    ConsentRecord,
    PrivacySettings,
    Term,
    ClassGroup, ClassSession, Enrollment, Holiday, Period, Room, Student, Subject, Teacher, TimetableEntry,
)


class TeacherSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='__str__', read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'name', 'employee_code', 'department']


class ClassGroupSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='enrollments.count', read_only=True)

    class Meta:
        model = ClassGroup
        fields = ['id', 'name', 'academic_year', 'student_count']
        validators = [
            UniqueTogetherValidator(queryset=ClassGroup.objects.all(), fields=['name', 'academic_year'], message='This class already exists for that academic year.'),
        ]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'code', 'name']


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'capacity']


class StudentSerializer(serializers.ModelSerializer):
    class_groups = serializers.PrimaryKeyRelatedField(many=True, queryset=ClassGroup.objects.all(), required=False)
    face_enrollment_count = serializers.SerializerMethodField()
    is_minor = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'roll_number', 'full_name', 'email', 'phone_number', 'is_active',
            'date_of_birth', 'guardian_name', 'guardian_contact',
            'consent_given', 'consent_recorded_at', 'consent_withdrawn_at', 'is_minor',
            'class_groups', 'face_enrollment_count', 'created_at',
        ]
        read_only_fields = ['consent_recorded_at', 'consent_withdrawn_at', 'created_at']

    def get_is_minor(self, student) -> bool | None:
        from .privacy import is_minor

        return is_minor(student)

    def get_face_enrollment_count(self, student) -> int:
        """Captures usable with the face model currently configured."""
        from vision.face.engine import configured_model_name

        return student.face_enrollments.filter(model_name=configured_model_name()).count()

    def _stamp_consent(self, validated_data, previous=False):
        if 'consent_given' in validated_data:
            given = validated_data['consent_given']
            if given and not previous:
                validated_data['consent_recorded_at'] = timezone.now()
            elif not given:
                validated_data['consent_recorded_at'] = None

    def create(self, validated_data):
        class_groups = validated_data.pop('class_groups', [])
        self._stamp_consent(validated_data)
        student = Student.objects.create(**validated_data)
        student.class_groups.set(class_groups)
        return student

    def update(self, instance, validated_data):
        class_groups = validated_data.pop('class_groups', None)
        self._stamp_consent(validated_data, previous=instance.consent_given)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if class_groups is not None:
            instance.class_groups.set(class_groups)
        if not instance.consent_given:
            # Withdrawing consent removes the student's stored face data.
            instance.face_enrollments.all().delete()
        return instance


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'class_group', 'enrolled_on']
        validators = [
            UniqueTogetherValidator(queryset=Enrollment.objects.all(), fields=['student', 'class_group'], message='Student is already enrolled in this class.'),
        ]


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ['id', 'number', 'name', 'weekday', 'specific_date', 'start_time', 'end_time']
        # Uniqueness and overlap are reported by Period.clean() with clearer messages.
        validators = []

    def validate(self, attrs):
        instance = self.instance or Period()
        candidate = Period(pk=instance.pk, **{
            field: attrs.get(field, getattr(instance, field, None))
            for field in ['number', 'name', 'weekday', 'specific_date', 'start_time', 'end_time']
        })
        try:
            candidate.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict if hasattr(error, 'error_dict') else error.messages)
        if candidate.same_scope().filter(number=candidate.number).exists():
            raise serializers.ValidationError({'number': 'This period number already exists for this day.'})
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'date', 'name']


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ['id', 'name', 'start_date', 'end_date', 'minimum_attendance']

    def validate(self, attrs):
        instance = Term(**{**{'name': '', 'start_date': None, 'end_date': None, 'minimum_attendance': 75}, **attrs})
        if self.instance:
            instance.pk = self.instance.pk
        instance.clean()
        return attrs


class TimetableEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableEntry
        fields = ['id', 'class_group', 'subject', 'teacher', 'room', 'weekday', 'period_number']
        validators = [
            UniqueTogetherValidator(queryset=TimetableEntry.objects.all(), fields=['class_group', 'weekday', 'period_number'], message='This class already has a subject in that period.'),
        ]

    def validate(self, attrs):
        def value(field):
            return attrs.get(field, getattr(self.instance, field, None))

        slot = TimetableEntry.objects.filter(weekday=value('weekday'), period_number=value('period_number'))
        if self.instance is not None:
            slot = slot.exclude(pk=self.instance.pk)
        if value('room') and slot.filter(room=value('room')).exists():
            raise serializers.ValidationError({'room': 'This room is already booked for that period.'})
        if value('teacher') and slot.filter(teacher=value('teacher')).exists():
            raise serializers.ValidationError({'teacher': 'This teacher already has a class in that period.'})
        return attrs


class ClassSessionSerializer(serializers.ModelSerializer):
    class_group_name = serializers.CharField(source='class_group.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)

    class Meta:
        model = ClassSession
        fields = [
            'id', 'class_group', 'class_group_name', 'subject', 'subject_code', 'teacher', 'room',
            'date', 'period_number', 'starts_at', 'ends_at', 'status', 'source',
        ]
        read_only_fields = ['source']

    def validate(self, attrs):
        starts_at = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends_at = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({'ends_at': 'End must be after start.'})
        period_number = attrs.get('period_number', getattr(self.instance, 'period_number', None))
        if period_number is not None:
            duplicate = ClassSession.objects.filter(
                class_group=attrs.get('class_group', getattr(self.instance, 'class_group', None)),
                date=attrs.get('date', getattr(self.instance, 'date', None)),
                period_number=period_number,
            )
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError({'period_number': 'This class already has a session for that period.'})
        return attrs


class ConsentRecordSerializer(serializers.ModelSerializer):
    recorded_by_username = serializers.CharField(source='recorded_by.username', read_only=True, default=None)

    class Meta:
        model = ConsentRecord
        fields = ['id', 'action', 'purpose', 'given_by', 'recorded_by_username', 'note', 'at']


class PrivacySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySettings
        fields = ['face_retention_days', 'attendance_retention_days', 'event_retention_days', 'blur_unconsented', 'updated_at']

    def validate(self, attrs):
        for field, value in attrs.items():
            if field.endswith('_days') and value > 36500:
                raise serializers.ValidationError({field: 'Use at most 36500 days (100 years), or 0 to keep indefinitely.'})
        return attrs
