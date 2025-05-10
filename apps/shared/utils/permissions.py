from rest_framework import permissions


class UserPermission(permissions.BasePermission):
    """
    Permission to check if user has 'create users with group' permission.
    """
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def has_permission(self, request, view):
        # Check if the user has the specified permission
        return request.user.has_perm(
            f'accounts.{self.permission_code}'
        )