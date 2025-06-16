# apps/customers/swagger.py

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.customers.serializers import CustomerSerializer, FullCustomerSerializer


def add_swagger_to_customer_viewset(viewset_cls):
    # Create Customer
    viewset_cls.create = swagger_auto_schema(
        tags=['Customers'],
        operation_summary="Create a new customer",
        operation_description=(
            "Register a new customer under the current organization. "
            "Returns the complete customer record including generated `customer_id` and creator info."
        ),
        request_body=CustomerSerializer,
        responses={
            201: openapi.Response(
                description="Customer created successfully",
                schema=FullCustomerSerializer()
            ),
            400: openapi.Response(
                description="Invalid customer data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Customer
    viewset_cls.update = swagger_auto_schema(
        tags=['Customers'],
        operation_summary="Update an existing customer",
        operation_description=(
            "Modify one or more attributes of a customer you own. "
            "Only active customers in your organization can be updated."
        ),
        request_body=CustomerSerializer,
        responses={
            200: openapi.Response(
                description="Customer updated successfully",
                schema=FullCustomerSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Attempt to update a customer outside your organization"),
            404: openapi.Response(description="Customer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Delete Customer
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Customers'],
        operation_summary="Delete a customer",
        operation_description=(
            "Soft-delete a customer by marking them inactive. "
            "Once deleted, the customer will no longer appear in listings."
        ),
        responses={
            204: openapi.Response(description="Customer deleted successfully"),
            404: openapi.Response(description="Customer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Customers'],
        operation_summary="Retrieve a customer",
        operation_description=(
            "Fetch the details of a specific customer by their primary key (`id`). "
            "Only active customers in your organization can be retrieved."
        ),
        responses={
            200: openapi.Response(
                description="Customer details retrieved successfully",
                schema=FullCustomerSerializer()
            ),
            404: openapi.Response(description="Customer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Customers
    viewset_cls.list = swagger_auto_schema(
        tags=['Customers'],
        operation_summary="List and filter customers",
        operation_description=(
            "Retrieve a paginated list of customers in your organization. "
            "Supports filtering by name, phone number, email, or customer_id."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by name, phone, email, or customer_id",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of customers",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_OBJECT, x_ref=FullCustomerSerializer.__name__)
                        ),
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
