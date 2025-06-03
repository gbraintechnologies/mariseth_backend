from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.shared.serializers.app_settings import AppSettingSerializer
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.shared.serializers.regions import RegionSerializer


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
