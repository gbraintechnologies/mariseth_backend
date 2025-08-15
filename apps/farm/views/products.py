from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farm, Product
from apps.farm.serializers.farm import FarmSerializer
from apps.farm.serializers.products import FullProductSerializer, ProductSerializer
from apps.farm.swaagger import add_swagger_to_product_viewset
from apps.farm.utils import build_product_filter_q
from apps.shared.literals import (
    CREATE_PRODUCT, DELETE_PRODUCT, GET_PRODUCT_MOVEMENT, LIST_PRODUCTS, UPDATE_PRODUCT,
    UPLOAD_PRODUCTS, VIEW_PRODUCT
)
from apps.shared.tasks.export_tasks import process_product_export
from apps.shared.utils.permissions import UserPermission
from apps.warehouse.models import WarehouseProductMovement
from apps.warehouse.serializers import WarehouseProductMovementSerializer


@add_swagger_to_product_viewset
class ProductViewSet(viewsets.GenericViewSet):
    serializer_class = FarmSerializer
    queryset = Product.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_PRODUCT,
            'update': UPDATE_PRODUCT,
            'retrieve': VIEW_PRODUCT,
            'list': LIST_PRODUCTS,
            'destroy': DELETE_PRODUCT,
            'upload_products': UPLOAD_PRODUCTS,
            'get_product_movement': GET_PRODUCT_MOVEMENT
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = ProductSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                FullProductSerializer(product).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = ProductSerializer(instance=product, data=request.data, partial=True,
                                           context={'request': request})
            if serializer.is_valid():
                product = serializer.save()
                return Response(
                    FullProductSerializer(product).data,
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def retrieve(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullProductSerializer(product).data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        export = request.query_params.get('export', 'false').lower()

        if export == 'true' and not request.query_params.get('type'):
            return Response({'error': 'Please select a product type.'}, status=status.HTTP_400_BAD_REQUEST)

        filter_q = build_product_filter_q(request.query_params, request.organization)

        products = Product.objects.select_related(
            'category', 'weight_metric', 'quantity_metric', 'created_by'
        ).filter(filter_q).order_by("-last_updated")

        # Handle export
        export_response = None
        if export == 'true':
            if not products.exists():
                export_response = 'No products to export.'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict()
                }
                process_product_export.delay(filter_params)
                export_response = 'Export started. You will receive an email when ready.'

        paginator = Paginator(products, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'export_response': export_response,
            'results': FullProductSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': products.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            product.soft_delete(owner=request.user)
            return Response(
                {'message': 'Product deleted successfully'},
                status=status.HTTP_200_OK
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['GET'], url_path='movement')
    def get_product_movement(self, request, pk=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        order_type = request.query_params.get('order_type', 'inflow')
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        warehouse_movements = WarehouseProductMovement.objects.filter(
            product=product,
            movement_type=order_type
        )

        paginator = Paginator(warehouse_movements, page_size)
        page_obj = paginator.get_page(page)
        results = WarehouseProductMovementSerializer(
            page_obj.object_list, many=True, context={'order_type': order_type}
        ).data

        return Response({
            'totals': {
                'total_quantity': warehouse_movements.aggregate(Sum('quantity'))['quantity__sum'],
                'total_weight': warehouse_movements.aggregate(Sum('weight'))['weight__sum'],
            },
            'results': results,
            'pagination': {
                'total': warehouse_movements.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='upload-product')
    @transaction.atomic
    def upload_products(self, request):
        pass
