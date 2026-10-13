from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AuditLog, NotificationPreference, Profile, Role, get_role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'role', 'password']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['role'] = get_role(instance)
        return data

    def create(self, validated_data):
        role = validated_data.pop('role', Role.VIEWER)
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'This field is required.'})
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Profile.objects.update_or_create(user=user, defaults={'role': role})
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if role is not None:
            Profile.objects.update_or_create(user=instance, defaults={'role': role})
        return instance


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['camera_offline', 'processing_failure', 'attendance_anomaly']


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ['id', 'actor', 'actor_username', 'action', 'target_type', 'target_id', 'detail', 'ip_address', 'created_at']
