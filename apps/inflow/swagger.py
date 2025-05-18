# views.py

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.inflow.serializers import DeliveryInspectionApprovalSerializer, FullInflowOrderSerializer, \
    InflowOrderSerializer


def add_swagger_to_inflow_viewset(viewset_cls):
    # Create Inflow Order
    viewset_cls.create = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Create a new inflow order",
        operation_description=(
            "Create a new inflow order under the current organization. "
            "`products` must include at least one item with valid `product` and `farm` IDs, `quantity` > 0, and `unit_price` >= 0. "
            "Optional fields: `additional_costs` (boolean), `additional_cost_amount` (numeric), `comments` (string). "
            "Returns the full InflowOrder with generated `order_id`, `serial_number` for each product, and computed totals."
        ),
        request_body=InflowOrderSerializer,
        responses={
            201: openapi.Response(
                description="Inflow order created successfully",
                schema=FullInflowOrderSerializer()
            ),
            400: openapi.Response(
                description="Invalid inflow order data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Inflow Order
    viewset_cls.update = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Update an existing inflow order",
        operation_description=(
            "Update an inflow order currently in `delivery_inspection` status only. "
            "Editable fields: `aggregator`, `procurement_officer`, `order_creation_date`, `expected_delivery_date`, "
            "`destination_warehouse`, `additional_costs`, `additional_cost_amount`, `comments`, and `products`. "
            "To modify existing products, include their `id`; to add new items, omit `id` with the same validation rules as creation."
        ),
        request_body=InflowOrderSerializer,
        responses={
            200: openapi.Response(
                description="Inflow order updated successfully",
                schema=FullInflowOrderSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Inflow order not found"),
            403: openapi.Response(description="Order cannot be updated in its current status"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Inflow Order
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Get details of a single inflow order",
        operation_description=(
            "Fetch full details of an active inflow order by its ID, including products, media_files, and history."
        ),
        responses={
            200: openapi.Response(
                description="Inflow order details returned",
                schema=FullInflowOrderSerializer()
            ),
            404: openapi.Response(description="Inflow order not found"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Inflow Orders
    viewset_cls.list = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="List and filter inflow orders",
        operation_description=(
            "Retrieve a paginated list of active inflow orders with optional filters: `status` (e.g., `order_approval`, `approved`), "
            "`destination_warehouse` (warehouse ID), `date_from` and `date_to` for `order_creation_date`, and text search on `order_id` or `comments`. "
            "Set `export=true` to initiate an export background task (pending implementation)."
        ),
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, "Filter by order status", type=openapi.TYPE_STRING),
            openapi.Parameter('warehouse', openapi.IN_QUERY, "Filter by destination warehouse ID",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Order creation date from (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Order creation date to (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('query', openapi.IN_QUERY, "Search by order_id or comments", type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY, "Set to 'true' to start export job",
                              type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of inflow orders",
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
                        ),
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid query parameters",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Inflow Order
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Delete an inflow order",
        operation_description=(
            "Soft-delete an inflow order. Only orders in `delivery_inspection` status can be deleted. "
            "This sets `is_active` to False and records the deleting user via `soft_delete()`."
        ),
        responses={
            204: openapi.Response(description="Inflow order deleted successfully"),
            400: openapi.Response(
                description="Cannot delete order in its current status",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Inflow order not found"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # Approve Delivery Inspection
    viewset_cls.approve_delivery_inspection = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Approve delivery inspection for an inflow order",
        operation_description=(
            "Approve the `delivery_inspection` step for an inflow order. Provide `complaints` list with `order_product_id` (int), "
            "`problematic_quantity` (<= ordered), `reason` (str), optional `comment` (str), and `images` as base64 strings. "
            "Quantities exceeding the ordered amount will be rejected."
        ),
        request_body=DeliveryInspectionApprovalSerializer,
        responses={
            200: openapi.Response(
                description="Delivery inspection approved",
                schema=FullInflowOrderSerializer()
            ),
            400: openapi.Response(
                description="Validation error in complaints or images",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Inflow order not found or not in delivery_inspection status"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.approve_delivery_inspection)

    # Approve Order
    viewset_cls.approve_order = swagger_auto_schema(
        tags=['Inflow Orders'],
        operation_summary="Approve an inflow order",
        operation_description=(
            "Finalize approval for an inflow order in `order_approval` status. "
            "Updates warehouse stock, sets `actual_delivery_date` to today, and logs history. No request body required."
        ),
        responses={
            200: openapi.Response(
                description="Order approved successfully",
                schema=FullInflowOrderSerializer()
            ),
            404: openapi.Response(description="Inflow order not found or not in order_approval status"),
        },
        security=[{'Bearer': []}]
    )(viewset_cls.approve_order)

    return viewset_cls
