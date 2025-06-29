from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.farm.serializers.farm import FarmDeleteSerializer, FarmProductDeleteSerializer, FarmSerializer, \
    FullFarmSerializer
from apps.farm.serializers.farmer import FarmerSerializer, FullFarmerSerializer
from apps.farm.serializers.products import FullProductSerializer, ProductSerializer


def add_swagger_to_farm_viewset(viewset_cls):
    # Create Farm
    viewset_cls.create = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="Create a new farm",
        operation_description=(
            "Register a new farm under the current organization. "
            "Returns the complete farm record including generated `farm_id` and associated products."
        ),
        request_body=FarmSerializer,
        responses={
            201: openapi.Response(
                description="Farm created successfully",
                schema=FullFarmSerializer()
            ),
            400: openapi.Response(
                description="Invalid farm data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Farm
    viewset_cls.update = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="Update an existing farm",
        operation_description=(
            "Modify one or more attributes of a farm you own. "
            "Only active farms in your organization can be updated."
        ),
        request_body=FarmSerializer,
        responses={
            200: openapi.Response(
                description="Farm updated successfully",
                schema=FullFarmSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            403: openapi.Response(description="Attempt to update a farm outside your organization"),
            404: openapi.Response(description="Farm not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Farm
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="Get details of a single farm",
        operation_description="Fetch full details of an active farm by its ID, including products and creator info.",
        responses={
            200: openapi.Response(
                description="Farm details returned",
                schema=FullFarmSerializer()
            ),
            404: openapi.Response(description="Farm not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Farms
    viewset_cls.list = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="List and filter farms",
        operation_description=(
            "Retrieve a paginated list of farms in your organization. "
            "Supports filtering by name/ID, type, size, crop type, or export initiation."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by name or farm_id", type=openapi.TYPE_STRING),
            openapi.Parameter('farm_type', openapi.IN_QUERY, "Filter by farm type", type=openapi.TYPE_STRING),
            openapi.Parameter('farm_size', openapi.IN_QUERY, "Filter by farm size", type=openapi.TYPE_STRING),
            openapi.Parameter('crop_type', openapi.IN_QUERY, "Filter by primary crop", type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY, "Set to 'true' to start export job",
                              type=openapi.TYPE_BOOLEAN, default=False),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Items per page", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Export: start date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Export: end date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('district', openapi.IN_QUERY, "Export: filter by district", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of farms (and export job status if requested)",
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
            400: openapi.Response(description="Missing required filter for export",
                                  schema=openapi.Schema(type=openapi.TYPE_OBJECT))
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Farm
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="Delete a farm",
        operation_description=(
            "Soft-delete a farm if no active farmers are assigned. "
            "Validates that all dependencies have been cleared first."
        ),
        request_body=FarmDeleteSerializer,
        responses={
            204: openapi.Response(description="Farm deleted successfully"),
            400: openapi.Response(description="Cannot delete farm with active farmers",
                                  schema=openapi.Schema(type=openapi.TYPE_OBJECT)),
            404: openapi.Response(description="Farm not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # # Upload Farms (Bulk)
    # viewset_cls.upload_farms = swagger_auto_schema(
    #     tags=['Farms'],
    #     operation_summary="Bulk upload farms",
    #     operation_description=(
    #         "Upload a CSV or Excel file to create multiple farms in one operation. "
    #         "You will be notified when processing completes."
    #     ),
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             'file': openapi.Schema(type=openapi.TYPE_FILE, description="CSV/Excel file of farm records")
    #         }
    #     ),
    #     responses={
    #         202: openapi.Response(description="File received, import job started"),
    #         400: openapi.Response(description="Invalid or missing upload file",
    #                               schema=openapi.Schema(type=openapi.TYPE_OBJECT))
    #     },
    #     security=[{'Bearer': []}]
    # )(viewset_cls.upload_farms)

    viewset_cls.delete_farm_products = swagger_auto_schema(
        tags=['Farms'],
        operation_summary="Remove products from a farm",
        operation_description="Deactivate specified products from the given farm in a single request.",
        request_body=FarmProductDeleteSerializer,
        responses={
            200: openapi.Response(description="Farm products deleted successfully"),
            400: openapi.Response(description="Invalid product IDs", schema=openapi.Schema(type=openapi.TYPE_OBJECT)),
            404: openapi.Response(description="Farm not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.delete_farm_products)

    return viewset_cls


def add_swagger_to_farmer_viewset(viewset_cls):
    viewset_cls.create = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="Register a new farmer",
        operation_description=(
            "Create a new farmer record under the current organization. "
            "Requires `name`, `type`, contact info, and optional `lead_farmer`. "
            "Assigns the farmer to the organization of the requesting user."
        ),
        request_body=FarmerSerializer,
        responses={
            201: openapi.Response(
                description="Farmer created successfully",
                schema=FullFarmerSerializer()
            ),
            400: openapi.Response(
                description="Invalid farmer data provided",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Farmer
    viewset_cls.update = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="Update an existing farmer",
        operation_description=(
            "Modify attributes of an active farmer in your organization. "
            "Only the fields provided will be updated."
        ),
        request_body=FarmerSerializer,
        responses={
            200: openapi.Response(
                description="Farmer updated successfully",
                schema=FarmerSerializer()
            ),
            400: openapi.Response(
                description="Validation errors or forbidden update",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Farmer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Farmer
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="Get a single farmer",
        operation_description="Fetch full details of an active farmer by ID, including linked farm and lead farmer.",
        responses={
            200: openapi.Response(
                description="Farmer details returned",
                schema=FullFarmerSerializer()
            ),
            404: openapi.Response(description="Farmer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Farmers
    viewset_cls.list = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="List and filter farmers",
        operation_description=(
            "Retrieve a paginated list of farmers in your organization. "
            "Supports filtering by `query` (name, phone, email, farm name or ID), "
            "`farmer_type`, `ownership_type`, `country`, `lead` (lead farmer ID), "
            "and initiating an export job (`export=true`). To export you have to choose a `farmer type`."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by name, phone, email, farm name or farmer_id",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('farmer_type', openapi.IN_QUERY, "Filter by farmer type", type=openapi.TYPE_STRING),
            openapi.Parameter('ownership_type', openapi.IN_QUERY, "Filter by farm land ownership",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('country', openapi.IN_QUERY, "Filter by country code", type=openapi.TYPE_STRING),
            openapi.Parameter('lead', openapi.IN_QUERY, "Filter smallholders by lead farmer ID",
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('export', openapi.IN_QUERY, "Set to 'true' to start export background job",
                              type=openapi.TYPE_BOOLEAN, default=False),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Results per page", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Export: start date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Export: end date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of farmers and optional export status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'export_response': openapi.Schema(type=openapi.TYPE_STRING,
                                                          description="Background export job message"),
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
            400: openapi.Response(description="Missing required `farmer_type` for export",
                                  schema=openapi.Schema(type=openapi.TYPE_OBJECT))
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Farmer
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="Delete a farmer",
        operation_description=(
            "Soft-delete an active farmer. "
            "Marks the farmer record inactive and records the deleting user."
        ),
        responses={
            204: openapi.Response(description="Farmer deleted successfully"),
            404: openapi.Response(description="Farmer not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    viewset_cls.get_smallholders_by_lead = swagger_auto_schema(
        tags=['Farmers'],
        operation_summary="Get smallholders by lead farmer ID",
        operation_description=(
            "Retrieve paginated list of smallholder farmers under a specific lead farmer\n\n"
            "Returns all active smallholder farmers (type='smallholder') that are "
            "associated with the specified lead farmer ID."
        ),
        manual_parameters=[
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term to filter smallholders (searches name, phone, email, farm name, farmer ID)",
                type=openapi.TYPE_STRING
            ),
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
            400: openapi.Response(
                description="Invalid request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: openapi.Response(
                description="Lead farmer not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.get_smallholders_by_lead)

    return viewset_cls
    # # Bulk Upload Farmers
    # viewset_cls.upload_farmers = swagger_auto_schema(
    #     tags=['Farmers'],
    #     operation_summary="Bulk upload farmers",
    #     operation_description=(
    #         "Upload a file (CSV/Excel) of farmer records to create multiple entries. "
    #         "A background job will process the file and notify on completion."
    #     ),
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             'file': openapi.Schema(type=openapi.TYPE_FILE, description="CSV or Excel file containing farmer data")
    #         }
    #     ),
    #     responses={
    #         202: openapi.Response(description="File accepted, export job started"),
    #         400: openapi.Response(description="Invalid or missing upload file",
    #                               schema=openapi.Schema(type=openapi.TYPE_OBJECT))
    #     },
    #     security=[{'Bearer': []}]
    # )(viewset_cls.upload_farmers)
    #
    return viewset_cls


def add_swagger_to_product_viewset(viewset_cls):
    # Create Product
    viewset_cls.create = swagger_auto_schema(
        tags=['Products'],
        operation_summary="Create a new product",
        operation_description=(
            "Register a new product under the current organization. "
            "Validates that if `type` is `livestock`, a `breed` must be provided."
        ),
        request_body=ProductSerializer,
        responses={
            201: openapi.Response(
                description="Product created successfully",
                schema=FullProductSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., missing breed for livestock or invalid fields)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.create)

    # Update Product
    viewset_cls.update = swagger_auto_schema(
        tags=['Products'],
        operation_summary="Update an existing product",
        operation_description=(
            "Modify one or more attributes of an active product in your organization. "
            "You cannot update products belonging to other organizations. "
            "Season dates must satisfy `season_start <= season_end`."
        ),
        request_body=ProductSerializer,
        responses={
            200: openapi.Response(
                description="Product updated successfully",
                schema=FullProductSerializer()
            ),
            400: openapi.Response(
                description="Validation error (e.g., invalid date range or missing breed for livestock)",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: openapi.Response(description="Product not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.update)

    # Retrieve Product
    viewset_cls.retrieve = swagger_auto_schema(
        tags=['Products'],
        operation_summary="Get a product by ID",
        operation_description="Fetch full details of an active product you own, including metrics, category, and creator info.",
        responses={
            200: openapi.Response(
                description="Product details returned",
                schema=FullProductSerializer()
            ),
            404: openapi.Response(description="Product not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.retrieve)

    # List Products
    viewset_cls.list = swagger_auto_schema(
        tags=['Products'],
        operation_summary="List and filter products",
        operation_description=(
            "Retrieve a paginated list of products in your organization. "
            "Supports filtering by name or type (`query`), `type`, `category`, `status`, `season_status`, "
            "creation date range, last-updated date range, and initiating an export job (`export=true`)."
        ),
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, "Search by name or product_id", type=openapi.TYPE_STRING),
            openapi.Parameter('type', openapi.IN_QUERY, "Filter by product type ('crops', 'livestock')",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, "Filter by category ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, "Filter by product status", type=openapi.TYPE_STRING),
            openapi.Parameter('season_status', openapi.IN_QUERY, "Filter by season status", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, "Filter by creation start date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, "Filter by creation end date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('last_updated_from', openapi.IN_QUERY, "Filter by last-updated start date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('last_updated_to', openapi.IN_QUERY, "Filter by last-updated end date (YYYY-MM-DD)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY,
                              "Set to 'true' to start export background job (requires `type`)",
                              type=openapi.TYPE_BOOLEAN, default=False),
            openapi.Parameter('page', openapi.IN_QUERY, "Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, "Results per page", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of products and optional export job message",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'export_response': openapi.Schema(type=openapi.TYPE_STRING,
                                                          description="Background export initiation message"),
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
                description="Missing required `type` when `export=true` or invalid filter values",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        },
        security=[{'Bearer': []}]
    )(viewset_cls.list)

    # Delete Product
    viewset_cls.destroy = swagger_auto_schema(
        tags=['Products'],
        operation_summary="Delete a product",
        operation_description="Soft-delete an active product you own. Marks it inactive and records the deleting user.",
        responses={
            204: openapi.Response(description="Product deleted successfully"),
            404: openapi.Response(description="Product not found")
        },
        security=[{'Bearer': []}]
    )(viewset_cls.destroy)

    # Bulk Upload Products
    # viewset_cls.upload_products = swagger_auto_schema(
    #     tags=['Products'],
    #     operation_summary="Bulk upload products",
    #     operation_description=(
    #         "Upload a file (CSV or Excel) containing multiple product records. "
    #         "A background task will process and import them, notifying on completion."
    #     ),
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             'file': openapi.Schema(type=openapi.TYPE_FILE, description="CSV/Excel file of products")
    #         }
    #     ),
    #     responses={
    #         202: openapi.Response(description="File received, export job started"),
    #         400: openapi.Response(description="Invalid or missing upload file", schema=openapi.Schema(type=openapi.TYPE_OBJECT))
    #     },
    #     security=[{'Bearer': []}]
    # )(viewset_cls.upload_products)

    return viewset_cls


