from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.shared.serializers.app_settings import AppSettingSerializer
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.shared.serializers.regions import RegionSerializer
from apps.shared.serializers.help import HelpSerializer, FullHelpSerializer


def add_swagger_to_custom_type_viewset(viewset_cls):
    # Create CustomType
    viewset_cls.create = swagger_auto_schema(
        tags=['Custom-Types'],
        operation_summary="Create a new custom type",
        operation_description=(
            "Create a custom type within your organization. "
            "Name must be unique among existing org and default types. "
            "Assigns creator and organization automatically."
        ),
        request_body=CustomTypeSerializer,
        responses={
            201: openapi.Response(
                description="Custom type created successfully",
                schema=CustomTypeSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., duplicate name)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update CustomType
    viewset_cls.update = swagger_auto_schema(
        tags=['Custom-Types'],
        operation_summary="Update an existing custom type",
        operation_description=(
            "Modify an active custom type in your organization. "
            "Default types cannot be updated and will return 403."
        ),
        request_body=CustomTypeSerializer,
        responses={
            200: openapi.Response(
                description="Custom type updated successfully",
                schema=CustomTypeSerializer()
            ),
            400: openapi.Response(
                description="Validation error or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Cannot update default custom type"),
            404: openapi.Response(description="Custom type not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Delete CustomType
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Custom-Types'],
        operation_summary="Delete a custom type",
        operation_description="Soft-delete a custom type, marking it inactive.",
        responses={
            204: openapi.Response(description="Custom type deleted successfully"),
            404: openapi.Response(description="Custom type not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # List CustomTypes
    viewset_cls.list = swagger_auto_schema(
        tags=['Custom-Types'],
        operation_summary="List custom types",
        operation_description=(
            "Retrieve a paginated list of your organization's custom types merged with default types. "
            "Optional `query` parameter filters by category_name."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Filter by category_name", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of custom types",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
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
    )(viewset_cls.list)

    return viewset_cls


def add_swagger_to_app_setting_viewset(view_cls):
    # Get or create settings
    view_cls.get_settings = swagger_auto_schema(
        tags=['App-Settings'],
        operation_summary="Retrieve application settings",
        operation_description=(
            "Fetch the active AppSetting for your organization. "
            "If none exist, a default setting is created."
        ),
        responses={
            200: openapi.Response(
                description="App settings retrieved successfully",
                schema=AppSettingSerializer()
            ),
            400: openapi.Response(
                description="Error creating default settings",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(view_cls.get_settings)

    # Create or update settings
    view_cls.create_or_update_settings = swagger_auto_schema(
        tags=['App-Settings'],
        operation_summary="Create or update application settings",
        operation_description=(
            "Update existing settings or create new AppSetting for your organization. "
            "Supports partial updates."
        ),
        request_body=AppSettingSerializer,
        responses={
            200: openapi.Response(
                description="App settings updated successfully",
                schema=AppSettingSerializer()
            ),
            201: openapi.Response(
                description="App settings created successfully",
                schema=AppSettingSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or invalid data",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(view_cls.create_or_update_settings)

    return view_cls


def add_swagger_to_region_viewset(view_cls):
    # List all regions
    view_cls.list = swagger_auto_schema(
        tags=['Common'],
        operation_summary="List all regions",
        operation_description="Retrieve a list of all Ghana regions with their districts",
        responses={
            200: openapi.Response(
                description="List of regions retrieved successfully",
                schema=RegionSerializer(many=True)
            )
        }
    )(view_cls.list)

    view_cls.retrieve = swagger_auto_schema(
        tags=['Common'],
        operation_summary="Retrieve region details",
        operation_description="Get detailed information about a specific region by its code",
        responses={
            200: openapi.Response(
                description="Region details retrieved successfully",
                schema=RegionSerializer()
            ),
            404: openapi.Response(
                description="Region not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Region with code 'XX' does not exist"
                        )
                    }
                )
            )
        }
    )(view_cls.retrieve)

    return view_cls



def add_swagger_to_dashboard_viewset(viewset_cls):
    # Document 'farmer_analysis' action
    viewset_cls.farmer_analysis = swagger_auto_schema(
        tags=['Dashboard'],
        operation_summary="Get farmer analysis statistics",
        operation_description=(
            "Retrieves aggregated statistics about farmers including:\n"
            "- Count of lead vs smallholder farmers\n"
            "- Gender distribution\n"
            "- Active warehouses count\n"
            "\nOptional date filtering available."
        ),
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Start date for filtering (YYYY-MM-DD format)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="End date for filtering (YYYY-MM-DD format)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
        ],
        responses={
            200: openapi.Response(
                description="Farmer analysis statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'lead_farmers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'smallholder_farmers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'active_warehouses': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'gender': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'male': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'female': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        ),
                        'farmer_type': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'lead_farmer': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'smallholder_farmer': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid date parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.farmer_analysis)

    return viewset_cls


def add_swagger_to_help_viewset(viewset_cls):
    # Create Help
    viewset_cls.create = swagger_auto_schema(
        tags=['Help'],
        operation_summary="Create a new help topic",
        operation_description="Create a new help topic for your organization.",
        request_body=HelpSerializer,
        responses={
            201: openapi.Response(
                description="Help topic created successfully",
                schema=FullHelpSerializer()
            ),
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Help
    viewset_cls.update = swagger_auto_schema(
        tags=['Help'],
        operation_summary="Update an existing help topic",
        operation_description="Update an existing help topic for your organization.",
        request_body=HelpSerializer,
        responses={
            200: openapi.Response(
                description="Help topic updated successfully",
                schema=HelpSerializer()
            ),
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Help topic not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Help
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Help'],
        operation_summary="Retrieve a specific help topic",
        operation_description="Get the details of a specific help topic by its ID.",
        responses={
            200: openapi.Response(
                description="The requested help topic.",
                schema=FullHelpSerializer()
            ),
            404: openapi.Response(description="Help topic not found.")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Help
    viewset_cls.list = swagger_auto_schema(
        tags=['Help'],
        operation_summary="List all help topics",
        operation_description="Retrieve a list of available help topics.",
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Filter by title or description", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of help",
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
    )(viewset_cls.list)

    # Delete Help
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Help'],
        operation_summary="Delete a help topic",
        operation_description="Soft-delete a help topic, marking it inactive.",
        responses={
            200: openapi.Response(description="Help deleted successfully"),
            404: openapi.Response(description="Help not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    return viewset_cls
