from rest_framework import serializers

from .models import Camera, ClassroomEvent, ObservationSettings


class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'source_type', 'source', 'room', 'is_enabled', 'created_at',
            'status', 'last_heartbeat', 'last_error', 'fps', 'latency_ms',
        ]
        read_only_fields = ['status', 'last_heartbeat', 'last_error', 'fps', 'latency_ms']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = instance.live_status
        return data

    def validate(self, attrs):
        source_type = attrs.get('source_type', getattr(self.instance, 'source_type', Camera.SourceType.WEBCAM))
        source = attrs.get('source', getattr(self.instance, 'source', ''))
        if source_type == Camera.SourceType.WEBCAM and not source.isdigit():
            raise serializers.ValidationError({'source': 'A webcam source is a device index such as 0.'})
        if source_type == Camera.SourceType.RTSP and not source.lower().startswith(('rtsp://', 'rtsps://')):
            raise serializers.ValidationError({'source': 'An RTSP source must start with rtsp://'})
        if source_type == Camera.SourceType.HTTP and not source.lower().startswith(('http://', 'https://')):
            raise serializers.ValidationError({'source': 'An HTTP source must start with http:// or https://'})
        return attrs


class ClassroomEventSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True, default=None)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)

    class Meta:
        model = ClassroomEvent
        fields = [
            'id', 'session', 'camera', 'kind', 'kind_label', 'student', 'student_name', 'started_at', 'ended_at',
            'confidence', 'summary', 'signals', 'review_status', 'reviewed_by_username', 'reviewed_at',
        ]


class ObservationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObservationSettings
        fields = [
            'hand_raise_enabled', 'head_down_enabled', 'phone_enabled', 'unusual_activity_enabled',
            'hand_raise_seconds', 'head_down_seconds', 'phone_seconds', 'unusual_activity_seconds', 'updated_at',
        ]

    def validate(self, attrs):
        for field, value in attrs.items():
            if field.endswith('_seconds') and not 0.5 <= value <= 3600:
                raise serializers.ValidationError({field: 'Use a duration between 0.5 and 3600 seconds.'})
        return attrs
