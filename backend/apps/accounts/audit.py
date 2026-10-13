from .models import AuditLog


def record(request, action: str, instance, detail: dict | None = None) -> None:
    """Write one audit entry for an operation on `instance`."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip_address = forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target_type=instance._meta.label,
        target_id=str(instance.pk),
        detail=detail or {},
        ip_address=ip_address or None,
    )


class AuditedModelViewSetMixin:
    """Audit create, update and delete on a ModelViewSet."""

    def perform_create(self, serializer):
        instance = serializer.save()
        record(self.request, 'create', instance)

    def perform_update(self, serializer):
        changed = sorted(serializer.validated_data.keys())
        instance = serializer.save()
        record(self.request, 'update', instance, {'fields': changed})

    def perform_destroy(self, instance):
        record(self.request, 'delete', instance, {'repr': str(instance)})
        instance.delete()
