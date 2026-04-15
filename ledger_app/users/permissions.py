from rest_framework.permissions import BasePermission
from rest_framework.views import Request
from .models import User


class IsAdminUser(BasePermission):
    """
    Grants access only to users whose is_admin flag is True.
    Requires JWTAuthentication to have already resolved request.user.
    """

    message = "You do not have permission to perform this action. Admin access required."

    def has_permission(self, request: Request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )
