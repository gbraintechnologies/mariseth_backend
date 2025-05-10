from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.serializers.auth import (AccountVerificationSerializer, ForgotPasswordSerializer, LoginSerializer,
                                            LogoutSerializer, ResendVerificationCodeSerializer, ResetPasswordSerializer,
                                            UpdateAccount, UpdatePasswordSerializer, UserWithTokenSerializer, )
from apps.accounts.serializers.users import GroupSerializer, GroupWithRankSerializer, NewUserSerializer, \
    PermissionSerializer, UserSerializer


def add_swagger_to_user_account_viewset(viewset_cls):
    # Create (Register Admin)
    viewset_cls.create = swagger_auto_schema(
        tags=['Admins'],
        operation_summary="Register a new admin user",
        operation_description=(
            "Create a new admin‐type user under your organization. "
            "If a `group` is provided, it must belong to the same organization or be a default group."
        ),
        request_body=NewUserSerializer,
        responses={
            201: openapi.Response(
                description="Admin user created successfully",
                schema=UserSerializer()
            ),
            400: openapi.Response("Validation errors or invalid payload")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update
    viewset_cls.update = swagger_auto_schema(
        tags=['Admins'],
        operation_summary="Update an existing admin user",
        operation_description=(
            "Partially or fully update attributes of an existing admin user. "
            "Only active users can be updated."
        ),
        request_body=NewUserSerializer,
        responses={
            200: openapi.Response(
                description="Admin user updated successfully",
                schema=UserSerializer()
            ),
            400: openapi.Response("Validation errors or invalid payload"),
            404: openapi.Response("User not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Destroy (Soft‐delete)
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Admins'],
        operation_summary="Deactivate (soft-delete) an admin user",
        operation_description=(
            "Soft-delete an admin user by encrypting PII fields (`email`, `username`, `phone_number`). "
            "Default users cannot be deleted."
        ),
        responses={
            200: openapi.Response(
                description="User soft-deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("Cannot delete default user"),
            404: openapi.Response("User not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # List
    viewset_cls.list = swagger_auto_schema(
        tags=['Admins'],
        operation_summary="List all admin users",
        operation_description=(
            "Retrieve a paginated list of active admin users in your organization. "
            "You can filter by `query` (name/email/phone), and control pagination."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY,
                              description="Search term (first_name, last_name, email, phone)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER,
                              default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Results per page", type=openapi.TYPE_INTEGER,
                              default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of admin users",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                  items=openapi.Items(type=openapi.TYPE_OBJECT)),
                        'pagination': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'has_next': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'has_previous': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response("Organization context missing")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Retrieve
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Admins'],
        operation_summary="Get details of a single admin user",
        operation_description="Fetch all profile fields for an active admin user by their ID.",
        responses={
            200: openapi.Response(description="Admin user data", schema=UserSerializer()),
            404: openapi.Response("User not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    return viewset_cls


def add_swagger_to_groups_view(viewset_cls):
    # List Groups
    viewset_cls.list = swagger_auto_schema(
        tags=['Groups'],
        operation_summary="List all groups",
        operation_description=(
            "Return both default and organization-specific groups, ordered by rank then name."
        ),
        responses={
            200: openapi.Response(
                description="A list of all active and default groups",
                schema=GroupSerializer(many=True)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Create Group
    viewset_cls.create = swagger_auto_schema(
        tags=['Groups'],
        operation_summary="Create a new group",
        operation_description=(
            "Add a new group with rank, description, and permissions."
        ),
        request_body=GroupWithRankSerializer,
        responses={
            201: openapi.Response(
                description="Group created successfully",
                schema=GroupSerializer()
            ),
            400: openapi.Response(
                description="Invalid data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Group
    viewset_cls.update = swagger_auto_schema(
        tags=['Groups'],
        operation_summary="Update an existing group",
        operation_description="Modify name, rank, description or permissions of an active group.",
        request_body=GroupWithRankSerializer,
        responses={
            200: openapi.Response(
                description="Group updated successfully",
                schema=GroupSerializer()
            ),
            400: openapi.Response(
                description="Invalid data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response("Group not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Delete Group
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Groups'],
        operation_summary="Delete a group",
        operation_description=(
            "Soft-delete a group if it has no assigned users and is not default."
        ),
        responses={
            200: openapi.Response(
                description="Group deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'detail': openapi.Schema(type=openapi.TYPE_STRING)}
                )
            ),
            400: openapi.Response(
                description="Cannot delete – either default or has users",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response("Group not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    return viewset_cls


def add_swagger_to_permission_list_view(view_cls):
    view_cls.get = swagger_auto_schema(
        tags=['Permissions'],
        operation_summary="List custom permissions",
        operation_description=(
            "Retrieve all application-specific permissions, excluding Django's built-in permissions."
        ),
        responses={
            200: openapi.Response(
                description="A list of custom permissions",
                schema=PermissionSerializer(many=True)
            )
        },
        security=[{'Bearer': []}]
    )(view_cls.get)

    return view_cls


def add_swagger_to_user_auth_viewset(viewset_cls):
    # Login
    viewset_cls.login = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Authenticate user and issue tokens",
        operation_description=(
            "Validate email and password credentials. "
            "Returns access and refresh tokens plus user details if authentication succeeds."
        ),
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful, returns user info with tokens",
                schema=UserWithTokenSerializer()
            ),
            401: openapi.Response(description="Invalid credentials or inactive account")
        }
    )(viewset_cls.login)

    # Logout
    viewset_cls.logout = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Revoke refresh token and logout",
        operation_description=(
            "Blacklists the provided refresh token and logs out the user from the current session."
        ),
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'detail': openapi.Schema(type=openapi.TYPE_STRING)}
                )
            ),
            400: openapi.Response(description="Invalid refresh token provided")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.logout)

    # Update Password
    viewset_cls.update_password = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Change user password",
        operation_description=(
            "Require current password and new password. "
            "Validates old password before updating to new one."
        ),
        request_body=UpdatePasswordSerializer,
        responses={
            200: openapi.Response(description="Password updated successfully"),
            401: openapi.Response(description="Invalid old password or authentication required")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update_password)

    # Update Account
    viewset_cls.update_account = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Update user profile",
        operation_description=(
            "Modify user profile fields such as name, phone, avatar, or email. "
            "Requires authentication."
        ),
        request_body=UpdateAccount,
        responses={
            200: openapi.Response(
                description="Account updated successfully",
                schema=UserSerializer()
            ),
            400: openapi.Response(description="Invalid account data provided")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update_account)

    # Verify Account
    viewset_cls.verify_account = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Verify user account",
        operation_description=(
            "Validate the verification code sent via WhatsApp and mark the account as verified."
        ),
        request_body=AccountVerificationSerializer,
        responses={
            200: openapi.Response(
                description="Account verified successfully",
                schema=UserWithTokenSerializer()
            ),
            400: openapi.Response(description="Invalid email or code provided")
        }
    )(viewset_cls.verify_account)

    # Resend Verification Code
    viewset_cls.resend_verification_code = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Resend account verification code",
        operation_description="Send a new verification code to the user's email via WhatsApp.",
        request_body=ResendVerificationCodeSerializer,
        responses={
            200: openapi.Response(description="Verification code resent successfully"),
            400: openapi.Response(description="Invalid email or inactive user")
        }
    )(viewset_cls.resend_verification_code)

    # Forgot Password
    viewset_cls.forgot_password = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Initiate password reset",
        operation_description=(
            "Send a password reset code to the user's email. "
            "Uses the same code mechanism as account verification."
        ),
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(description="Password reset instructions sent"),
            400: openapi.Response(description="Email not found or inactive")
        }
    )(viewset_cls.forgot_password)

    # Reset Password
    viewset_cls.reset_password = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Complete password reset",
        operation_description=(
            "Validate reset code and set new password. "
            "Also marks account as verified."
        ),
        request_body=ResetPasswordSerializer,
        responses={
            200: openapi.Response(description="Password reset successfully"),
            400: openapi.Response(description="Invalid email or code provided")
        }
    )(viewset_cls.reset_password)

    # Me (Profile)
    viewset_cls.me = swagger_auto_schema(
        tags=['Authentication'],
        operation_summary="Get logged-in user info",
        operation_description="Return the authenticated user's profile details.",
        responses={
            200: openapi.Response(description="User profile returned", schema=UserSerializer()),
            401: openapi.Response(description="Authentication credentials were not provided")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.me)

    return viewset_cls
