from rest_framework import serializers

from .models import Camera


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
