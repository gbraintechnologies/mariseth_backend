from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farm, Product
from django.contrib.auth import get_user_model
from apps.shared.literals import CREATE_WAREHOUSE, DELETE_WAREHOUSE, GET_PRODUCT_WAREHOUSE_MOVEMENT,     GET_WAREHOUSE_INVENTORY, LIST_WAREHOUSES, UPDATE_WAREHOUSE, UPLOAD_WAREHOUSES, VIEW_WAREHOUSE,     ADD_REMOVE_WAREHOUSE_MANAGER

User = get_user_model()
from apps.shared.tasks.export_tasks import process_warehouse_export
from apps.shared.utils.permissions import UserPermission
from apps.warehouse.models import Warehouse, WarehouseProduct, WarehouseProductMovement
from apps.warehouse.serializers import (FullWarehouseProductSerializer, FullWarehouseSerializer,
                                        ManageManagerSerializer, WarehouseProductMovementSerializer,
                                        WarehouseSerializer)
from apps.warehouse.swagger import add_swagger_to_warehouse_viewset


@add_swagger_to_warehouse_viewset
class WarehouseViewSet(viewsets.GenericViewSet):
    serializer_class = WarehouseSerializer
    queryset = Warehouse.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_WAREHOUSE,
            'update': UPDATE_WAREHOUSE,
            'retrieve': VIEW_WAREHOUSE,
            'list': LIST_WAREHOUSES,
            'destroy': DELETE_WAREHOUSE,
            'upload_warehouses': UPLOAD_WAREHOUSES,
            'get_warehouse_inventory': GET_WAREHOUSE_INVENTORY,
            'get_product_warehouse_movement': GET_PRODUCT_WAREHOUSE_MOVEMENT,
            'manage_managers': ADD_REMOVE_WAREHOUSE_MANAGER
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = WarehouseSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            warehouse = serializer.save()
            return Response(FullWarehouseSerializer(warehouse).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            warehouse = Warehouse.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = WarehouseSerializer(instance=warehouse, data=request.data, partial=True,
                                             context={'request': request})
            if serializer.is_valid():
                warehouse = serializer.save()
                return Response(FullWarehouseSerializer(warehouse).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            warehouse = Warehouse.objects.prefetch_related('product_stocks').get(
                pk=pk, is_active=True, organization=request.organization
            )
            return Response(FullWarehouseSerializer(warehouse).data, status=status.HTTP_200_OK)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        region = request.query_params.get('region')
        district = request.query_params.get('district')
        export = request.query_params.get('export', 'false').lower()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        last_updated_from = request.query_params.get('last_updated_from')
        last_updated_to = request.query_params.get('last_updated_to')

        filter_q = Q(is_active=True, organization=request.organization)

        if region:
            filter_q &= Q(region=region)
        if district:
            filter_q &= Q(district=district)
        if date_from and date_to:
            filter_q &= Q(date_created__date__range=[date_from, date_to])
        if last_updated_from and last_updated_to:
            filter_q &= Q(date_modified__date__range=[last_updated_from, last_updated_to])
        if query:
            filter_q &= (
                    Q(name__icontains=query) |
                    Q(warehouse_id__icontains=query)
            )
        # Changed from select_related('manager') to prefetch_related('managers')
        # to correctly fetch the ManyToMany relationship for managers.
        warehouses = Warehouse.objects.prefetch_related('managers').filter(filter_q).order_by('date_created')

        # Handle export
        export_response = None
        if export == 'true':
            filter_params = {
                'user_id': request.user.id,
                'organization_id': request.organization.id,
                'query': query,
                'region': region,
                'district': district,
                'date_from': date_from,
                'date_to': date_to
            }
            process_warehouse_export.delay(filter_params)
            export_response = 'Export started. You will receive an email when ready.'

        paginator = Paginator(warehouses, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'export_response': export_response,
            'results': FullWarehouseSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': warehouses.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='add-remove-managers')
    @transaction.atomic
    def add_remove_managers(self, request, pk=None):
        """
        Add or remove a manager from a warehouse.
        """
        try:
            warehouse = Warehouse.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ManageManagerSerializer(data=request.data,warehouse=warehouse,organization=request.organization)
        serializer.is_valid(raise_exception=True)
        updated_warehouse = serializer.save()
        if getattr(serializer, 'updated', False):
            return Response(FullWarehouseSerializer(updated_warehouse).data, status=status.HTTP_200_OK)
        return Response({'message': serializer.message}, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        # TODO: ASK FURTHER IMFO ON WHAT HAPPENDS TO OTHER STUFF WHEN A WAREHOUSE IS DELETED
        try:
            warehouse = Warehouse.objects.get(pk=pk, is_active=True, organization=request.organization)
            warehouse.soft_delete(owner=request.user)
            warehouse.save()
            return Response({'message': 'Warehouse deleted successfully'}, status=status.HTTP_200_OK)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST'], url_path='upload-warehouse')
    def upload_warehouses(self, request):
        pass

    @action(detail=True, methods=['GET'], url_path='products')
    def get_warehouse_inventory(self, request, pk=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        try:
            warehouse = Warehouse.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
        warehouse_products = WarehouseProduct.objects.filter(warehouse=warehouse).order_by('-date_created')
        paginator = Paginator(warehouse_products, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullWarehouseProductSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': warehouse_products.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], url_path='product/(?P<product_id>[^/.]+)')
    def get_product_warehouse_movement(self, request, pk=None, product_id=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        order_type = request.query_params.get('order_type', 'inflow')
        try:
            warehouse = Warehouse.objects.get(pk=pk, is_active=True, organization=request.organization)
            product = Product.objects.get(pk=product_id, is_active=True, organization=request.organization)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        warehouse_movements = WarehouseProductMovement.objects.filter(
            warehouse=warehouse,
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
