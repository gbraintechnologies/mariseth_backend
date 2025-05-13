# apps/warehouse/swagger.py

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.warehouse.serializers import (FullWarehouseSerializer, WarehouseSerializer)


def add_swagger_to_warehouse_viewset(viewset_cls):
    # Create Warehouse
    viewset_cls.create = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="Create a new warehouse",
        operation_description=(
            "Register a new warehouse under the current organization. "
            "Returns the complete warehouse record including generated `warehouse_id` and associated products."
        ),
        request_body=WarehouseSerializer,
        responses={
            201: openapi.Response(
                description="Warehouse created successfully",
                schema=FullWarehouseSerializer()
            ),
            400: openapi.Response(
                description="Invalid warehouse data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Warehouse
    viewset_cls.update = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="Update an existing warehouse",
        operation_description=(
            "Modify one or more attributes of a warehouse you own. "
            "Only active warehouses in your organization can be updated."
        ),
        request_body=WarehouseSerializer,
        responses={
            200: openapi.Response(
                description="Warehouse updated successfully",
                schema=FullWarehouseSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Attempt to update a warehouse outside your organization"),
            404: openapi.Response(description="Warehouse not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Warehouse
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="Get details of a single warehouse",
        operation_description=(
            "Fetch full details of an active warehouse by its ID, including products and manager info."
        ),
        responses={
            200: openapi.Response(
                description="Warehouse details returned",
                schema=FullWarehouseSerializer()
            ),
            404: openapi.Response(description="Warehouse not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Warehouses
    viewset_cls.list = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="List and filter warehouses",
        operation_description=(
            "Retrieve a paginated list of warehouses in your organization. "
            "Supports filtering by name/ID, region, district, date ranges for creation or modification, "
            "and starting an export job."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by name or warehouse_id", type=openapi.TYPE_STRING),
            openapi.Parameter('region', openapi.IN_QUERY, "Filter by region", type=openapi.TYPE_STRING),
            openapi.Parameter('district', openapi.IN_QUERY, "Filter by district", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Created from (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Created to (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('last_updated_from', openapi.IN_QUERY, "Modified from (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('last_updated_to', openapi.IN_QUERY, "Modified to (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY, "Set to 'true' to start export job",
                              type=openapi.TYPE_BOOLEAN, default=False),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of warehouses (and export job status if requested)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'export_response': openapi.Schema(type=openapi.TYPE_STRING, description='Export job message'),
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
                description="Missing required filter for export",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Warehouse
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="Delete a warehouse",
        operation_description=(
            "Soft-delete a warehouse if no active products are assigned. "
            "Validates that all dependencies have been cleared first."
        ),
        responses={
            204: openapi.Response(description="Warehouse deleted successfully"),
            400: openapi.Response(
                description="Cannot delete warehouse with active products",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Warehouse not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # Bulk Upload Warehouses
    viewset_cls.upload_warehouses = swagger_auto_schema(
        tags=['Warehouses'],
        operation_summary="Bulk upload warehouses",
        operation_description=(
            "Upload a CSV or Excel file to create multiple warehouses in one operation. "
            "You will be notified when processing completes."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'file': openapi.Schema(type=openapi.TYPE_FILE, description="CSV/Excel file of warehouse records"),
            }
        ),
        responses={
            202: openapi.Response(description="File received, import job started"),
            400: openapi.Response(
                description="Invalid or missing upload file",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.upload_warehouses)

    return viewset_cls
