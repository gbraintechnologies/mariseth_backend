from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.serializers.auth import LogoutSerializer
from apps.consuner_mobile.serializers.auth import MobileAccountVerificationSerializer, MobileLoginSerializer, \
    MobileRegisterSerializer, MobileResendVerificationCodeSerializer, \
    MobileResetPasswordSerializer, MobileUpdateAccount, MobileUpdatePinSerializer, \
    MobileUserWithTokenAndFarmerSerializer, SetPinSerializer
from apps.consuner_mobile.serializers.credit import MobileActiveCreditSerializer
from apps.consuner_mobile.serializers.farm import FarmDetailSerializer


def add_swagger_to_mobile_user_auth_viewset(viewset_cls):
    # Login
    viewset_cls.login = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Mobile user login",
        operation_description=(
            "Authenticate a mobile user using phone number and PIN. "
            "Returns user data with access and refresh tokens upon successful authentication."
        ),
        request_body=MobileLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=MobileUserWithTokenAndFarmerSerializer()
            ),
            401: openapi.Response("Invalid credentials or user not authenticated")
        }
    )(viewset_cls.login)

    # Register
    viewset_cls.register = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Register a new mobile user",
        operation_description=(
            "Register a new mobile user by phone number. The phone number must be "
            "registered as a farmer first. A verification code will be sent to the phone number."
        ),
        request_body=MobileRegisterSerializer,
        responses={
            201: openapi.Response(
                description="Registration successful, verification code sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("Validation errors or phone number not registered as farmer")
        }
    )(viewset_cls.register)

    # Verify Phone
    viewset_cls.verify_phone = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Verify phone number with code",
        operation_description=(
            "Verify the phone number using the verification code sent during registration. "
            "After successful verification, user needs to setup their PIN."
        ),
        request_body=MobileAccountVerificationSerializer,
        responses={
            200: openapi.Response(
                description="Verification successful, setup PIN required",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("Invalid verification code or validation errors")
        }
    )(viewset_cls.verify_phone)

    # Setup PIN
    viewset_cls.set_pin = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Setup PIN for new user",
        operation_description=(
            "Set a 4-digit PIN for a newly registered user or after password reset. "
            "Returns user data with tokens upon successful PIN setup."
        ),
        request_body=SetPinSerializer,
        responses={
            200: openapi.Response(
                description="PIN setup successful",
                schema=MobileUserWithTokenAndFarmerSerializer()
            ),
            400: openapi.Response("Validation errors or user not found")
        }
    )(viewset_cls.set_pin)

    # Logout
    viewset_cls.logout = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Logout mobile user",
        operation_description="Logout the authenticated mobile user and invalidate their session.",
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("Validation errors")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.logout)

    # Update PIN
    viewset_cls.update_pin = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Update user PIN",
        operation_description=(
            "Update the authenticated user's PIN by providing the old PIN and new PIN. "
            "User must be authenticated to perform this action."
        ),
        request_body=MobileUpdatePinSerializer,
        responses={
            200: openapi.Response(
                description="PIN updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response("Invalid old PIN or authentication required")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update_pin)

    # Update Account
    viewset_cls.update_account = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Update user account details",
        operation_description=(
            "Update the authenticated user's account information such as name, phone number, "
            "email, avatar, and gender. Partial updates are supported."
        ),
        request_body=MobileUpdateAccount,
        responses={
            200: openapi.Response(
                description="Account updated successfully",
                schema=MobileUpdateAccount()
            ),
            400: openapi.Response("Validation errors")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update_account)

    # Resend Verification Code
    viewset_cls.resend_verification_code = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Resend verification code",
        operation_description=(
            "Resend a new verification code to the user's phone number. "
            "Useful when the original code expires or is not received."
        ),
        request_body=MobileResendVerificationCodeSerializer,
        responses={
            200: openapi.Response(
                description="Verification code sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("User not found or validation errors")
        }
    )(viewset_cls.resend_verification_code)

    # Forgot Password
    viewset_cls.forgot_password = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Initiate forgot password process",
        operation_description=(
            "Initiate the forgot password process by sending a verification code "
            "to the user's registered phone number."
        ),
        request_body=MobileResendVerificationCodeSerializer,
        responses={
            200: openapi.Response(
                description="Password reset code sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("User not found or validation errors")
        }
    )(viewset_cls.forgot_password)

    # Reset Password
    viewset_cls.reset_password = swagger_auto_schema(
        tags=['Mobile/Auth'],
        operation_summary="Reset user password",
        operation_description=(
            "Reset the user's password using the verification code sent to their phone number "
            "and set a new PIN. The user will be automatically verified after successful reset."
        ),
        request_body=MobileResetPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password reset successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response("Invalid verification code or validation errors")
        }
    )(viewset_cls.reset_password)

    return viewset_cls


# ============================== MOBILE/CREDIT ==============================
def add_swagger_to_mobile_credit_viewset(viewset_cls):
    # Get Active Credit
    viewset_cls.get_active_credit = swagger_auto_schema(
        tags=["Mobile/Credit"],
        operation_summary="Get active credit for the logged-in farmer",
        operation_description="Fetch the active credit details for the current farmer.",
        responses={
            200: openapi.Response(
                description="Active credit details returned",
                schema=MobileActiveCreditSerializer()
            ),
            404: openapi.Response(description="No active credit found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_active_credit)

    # Get Credit History
    viewset_cls.get_credit_history = swagger_auto_schema(
        tags=["Mobile/Credit"],
        operation_summary="Get credit history for the logged-in farmer",
        operation_description="Retrieve a paginated list of credits for the current farmer.",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('status', openapi.IN_QUERY, "Filter by payment status", type=openapi.TYPE_STRING),
            openapi.Parameter('type', openapi.IN_QUERY, "Filter by credit type", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of credits",
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
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_credit_history)

    # Get Payback History
    viewset_cls.get_payback_history = swagger_auto_schema(
        tags=["Mobile/Credit"],
        operation_summary="Get payback history for the logged-in farmer",
        operation_description="Retrieve a paginated list of paybacks for the current farmer.",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('credit_id', openapi.IN_QUERY, "Filter by credit ID", type=openapi.TYPE_STRING),
            openapi.Parameter('method', openapi.IN_QUERY, "Filter by payback method", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of paybacks",
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
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_payback_history)

    return viewset_cls


# ============================== MOBILE/LEAD FARMER ==============================

def add_swagger_to_mobile_lead_farmer_viewset(viewset_cls):
    # Document get_farms endpoint
    viewset_cls.get_farms = swagger_auto_schema(
        tags=['Mobile/Lead Farmer'],
        operation_summary="Get lead farmer's farms",
        operation_description="Retrieve paginated list of farms owned by the authenticated lead farmer",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Items per page",
                type=openapi.TYPE_INTEGER,
                default=10
            ),
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term to filter farms (searches name, farm_id, location)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of farms",
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
            403: openapi.Response(
                description="Forbidden - User is not a lead farmer",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_farms)

    # Document get_smallholders endpoint
    viewset_cls.get_smallholders = swagger_auto_schema(
        tags=['Mobile/Lead Farmer'],
        operation_summary="Get lead farmer's smallholders",
        operation_description="Retrieve paginated list of smallholder farmers under the authenticated lead farmer",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Items per page",
                type=openapi.TYPE_INTEGER,
                default=10
            ),
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term to filter smallholders (searches name, farmer_id, phone, farm name)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of smallholder farmers",
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
            403: openapi.Response(
                description="Forbidden - User is not a lead farmer",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_smallholders)

    return viewset_cls


def add_swagger_to_mobile_farm_viewset(viewset_cls):
    viewset_cls.get_my_farm = swagger_auto_schema(
        tags=['Mobile/Farm'],
        operation_summary="Get current user's farm details",
        operation_description="Retrieve complete farm details for the authenticated user",
        responses={
            200: openapi.Response(
                description="Farm details",
                schema=FarmDetailSerializer()
            ),
            404: openapi.Response(
                description="Farm not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_my_farm)

    return viewset_cls
