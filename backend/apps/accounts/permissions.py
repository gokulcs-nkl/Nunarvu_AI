from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role, get_role

ALL_ROLES = (Role.ADMIN, Role.TEACHER, Role.VIEWER)
STAFF_ROLES = (Role.ADMIN, Role.TEACHER)
ADMIN_ONLY = (Role.ADMIN,)


class RolePermission(BasePermission):
    """
    Role check driven by two view attributes:
    `read_roles` (default: every role) and `write_roles` (default: administrators only).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            allowed = getattr(view, 'read_roles', ALL_ROLES)
        else:
            allowed = getattr(view, 'write_roles', ADMIN_ONLY)
        return get_role(user) in allowed
