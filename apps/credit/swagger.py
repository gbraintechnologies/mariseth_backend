from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.credit.serializers.credits import CreditApprovalSerializer, CreditSerializer, FullCreditSerializer
from apps.credit.serializers.payback import CreditPaybackSerializer, FullPaybackSerializer


def add_swagger_to_credit_viewset(viewset_cls):
    # Create Credit
    viewset_cls.create = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="Create a new credit record",
        operation_description=(
            "Register a new credit issuance for a farmer under the current organization. "
            "Validates that `due_date` is strictly after `issue_date`."
        ),
        request_body=CreditSerializer,
        responses={
            201: openapi.Response(
                description="Credit created successfully",
                schema=FullCreditSerializer()
            ),
            400: openapi.Response(
                description=(
                    "Validation error (e.g., missing or malformed fields, "
                    "`due_date` must be after `issue_date`)."
                ),
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Credit
    viewset_cls.update = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="Update an existing credit",
        operation_description=(
            "Modify one or more attributes of an active credit in your organization. "
            "You may only update credits you own, and `due_date` must remain after `issue_date`."
        ),
        request_body=CreditSerializer,
        responses={
            200: openapi.Response(
                description="Credit updated successfully",
                schema=FullCreditSerializer()
            ),
            400: openapi.Response(
                description=(
                    "Validation error (e.g., invalid date range or attempt to update "
                    "a credit outside your organization)."
                ),
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Credit not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Credit
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="Get a credit by ID",
        operation_description="Fetch full details of an active credit you own, including approval status and outstanding amount.",
        responses={
            200: openapi.Response(
                description="Credit details returned",
                schema=FullCreditSerializer()
            ),
            404: openapi.Response(description="Credit not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List & Filter Credits
    viewset_cls.list = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="List and filter credits",
        operation_description=(
            "Retrieve a paginated list of credits in your organization. "
            "Supports filtering by ID or farmer name (`query`), `payment_status`, `input_type`, "
            "issue date range, and initiating a CSV export (`export=true`)."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by credit ID or farmer name",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('payment_status', openapi.IN_QUERY, "Filter by payment status (e.g., 'paid', 'unpaid')",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('input_type', openapi.IN_QUERY, "Filter by credit type (e.g., 'feed', 'seed')",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Filter by issue date start (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Filter by issue date end (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY, "Set to 'true' to enqueue a CSV export task",
                              type=openapi.TYPE_BOOLEAN, default=False),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Results per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of credits (and optional export initiation message)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'export_response': openapi.Schema(type=openapi.TYPE_STRING,
                                                          description="Background export initiation message, if requested"),
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
            400: openapi.Response(
                description="Invalid filter values",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Credit
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="Delete a credit",
        operation_description=(
            "Soft-delete an inactive credit you own. "
            "Only credits with `approval_status='inactive'` and no active paybacks may be deleted."
        ),
        responses={
            204: openapi.Response(description="Credit deleted successfully"),
            400: openapi.Response(
                description=(
                    "Cannot delete: credit is still active or has outstanding paybacks."
                ),
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Credit not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # # Bulk Upload Credits
    # viewset_cls.upload_credits = swagger_auto_schema(
    #     tags=['Credits'],
    #     operation_summary="Bulk upload credits",
    #     operation_description=(
    #         "Upload a CSV or Excel file containing multiple credit records. "
    #         "A background task will process the file and notify you upon completion."
    #     ),
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             'file': openapi.Schema(type=openapi.TYPE_FILE, description="CSV/Excel file of credits")
    #         }
    #     ),
    #     responses={
    #         202: openapi.Response(description="File received; export job started"),
    #         400: openapi.Response(description="Invalid or missing upload file", schema=openapi.Schema(type=openapi.TYPE_OBJECT))
    #     },
    #     security=[{'Bearer': []}]
    # )(viewset_cls.upload_credits)

    # Approve or Deny Credit
    viewset_cls.approve_deny_credit = swagger_auto_schema(
        tags=['Credits'],
        operation_summary="Approve or deny a credit application",
        operation_description=(
            "Perform an approval or denial on a pending credit. "
            "`action` must be 'approve' or 'deny'. If denying, `denial_notes` is required."
        ),
        request_body=CreditApprovalSerializer,
        responses={
            200: openapi.Response(
                description="Credit approval status updated",
                schema=FullCreditSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., already approved/denied, missing `denial_notes`)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Credit not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.approve_deny_credit)

    return viewset_cls


def add_swagger_to_payback_viewset(viewset_cls):
    # Create Payback
    viewset_cls.create = swagger_auto_schema(
        tags=['Paybacks'],
        operation_summary="Create a new payback record",
        operation_description=(
            "Record a payment against a credit. The payment amount must be a positive decimal "
            "not exceeding the current outstanding amount of the credit. "
            "If the payment fully covers the outstanding amount, the credit status is set to 'paid'; "
            "otherwise it remains 'partial'. Product and quantity_bags are optional and only required "
            "when tracking physical goods. "
            "Date_paid and status fields are read-only and will be auto-populated."
        ),
        request_body=CreditPaybackSerializer,
        responses={
            201: openapi.Response(
                description="Payback created successfully",
                schema=FullPaybackSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., amount exceeds outstanding, missing required fields)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Forbidden: insufficient permissions to create payback"),
            404: openapi.Response(description="Credit not found or inactive"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Payback
    viewset_cls.update = swagger_auto_schema(
        tags=['Paybacks'],
        operation_summary="Update an existing payback record",
        operation_description=(
            "Modify the payment amount or associated details of an existing payback. "
            "Adjusting the payment amount will recalculate the outstanding balance of the associated credit "
            "and update its payment status accordingly. Only amount, product, quantity_bags, and comments can be updated. "
            "The `date_paid` remains unchanged and `status` is recalculated based on the new outstanding amount."
        ),
        request_body=CreditPaybackSerializer,
        responses={
            200: openapi.Response(
                description="Payback updated successfully",
                schema=FullPaybackSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., new amount invalid)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Forbidden: insufficient permissions to update payback"),
            404: openapi.Response(description="Payback not found or inactive"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # List Paybacks
    viewset_cls.list = swagger_auto_schema(
        tags=['Paybacks'],
        operation_summary="Retrieve a list of payback records",
        operation_description=(
            "Fetch a paginated list of paybacks for credits within the current organization. "
            "Supports filtering by:\n"
            "- `credit`: ID of the credit record\n"
            "- `method`: payment method (e.g., 'cash', 'transfer')\n"
            "- `date_from` and `date_to`: date paid range (YYYY-MM-DD)\n"
            "- `status`: payment status ('paid', 'partial')\n"
            "If `date_from` is specified, `date_to` must also be provided. "
            "Results are ordered by `date_paid` descending."
        ),
        manual_parameters=[
            openapi.Parameter('credit', openapi.IN_QUERY,
                              description="Filter by credit ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('method', openapi.IN_QUERY,
                              description="Filter by payback method code", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY,
                              description="Start date for date_paid filter (inclusive), format YYYY-MM-DD",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY,
                              description="End date for date_paid filter (inclusive), format YYYY-MM-DD",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY,
                              description="Filter by status code ('paid', 'partial')", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY,
                              description="Page number (default: 1)", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY,
                              description="Number of items per page (default: 10)", type=openapi.TYPE_INTEGER,
                              default=10),
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
            ),
            400: openapi.Response(description="Invalid query parameters",
                                  schema=openapi.Schema(type=openapi.TYPE_OBJECT)),
            403: openapi.Response(description="Forbidden: insufficient permissions to list paybacks"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    return viewset_cls
