from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse
from apps.outflow.serializers.approvals import MarkOrderPickedSerializer, \
    OutflowOrderApprovalSerializer, OutflowWarehouseListSerializer, OutflowWarehouseOrderDetailSerializer, \
    WarehouseVerificationSerializer
from apps.outflow.utils import build_outflow_filter_q
from apps.shared.literals import LIST_OUTFLOW_APPROVAL, MARK_OUTFLOW_ORDER_PICKED, VERIFY_OUTFLOW_AVAILABILITY, \
    VIEW_OUTFLOW_APPROVAL
from apps.shared.tasks.export_tasks import process_outflow_export
from apps.shared.utils.permissions import UserPermission


class OutflowApprovalViewSet(viewsets.GenericViewSet):
    queryset = OutflowOrder.objects.filter(is_active=True)
    serializer_class = OutflowOrderApprovalSerializer

    def get_permissions(self):
        permissions = {
            'retrieve': VIEW_OUTFLOW_APPROVAL,
            'list_outflow_orders': LIST_OUTFLOW_APPROVAL,
            'verify_availability': VERIFY_OUTFLOW_AVAILABILITY,
            'mark_order_picked': MARK_OUTFLOW_ORDER_PICKED
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='warehouse/(?P<warehouse_id>[^/.]+)')
    def retrieve_outflow_order_warehouse(self, request, pk=None, warehouse_id=None):
        """
        Retrieves one OutflowOrderWarehouse for a given OutflowOrder,
        limited to the logged-in manager’s warehouse.
        """
        try:
            order = OutflowOrder.objects.select_related('customer', 'procurement_officer').get(
                pk=pk,
                organization=request.organization
            )
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow Order not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            warehouse = OutflowOrderWarehouse.objects.select_related('warehouse').get(
                pk=warehouse_id,
                outflow_order=order,
                warehouse__managers__in=[request.user]
            )
        except OutflowOrderWarehouse.DoesNotExist:
            return Response({'error': 'Warehouse Order not found or not assigned to you'},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = OutflowWarehouseOrderDetailSerializer(warehouse)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='list-outflow-orders')
    def list_outflow_orders(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        export = request.query_params.get('export', 'false').lower()

        qs = OutflowOrderWarehouse.objects.select_related(
            'outflow_order', 'warehouse',
            'outflow_order__customer',
            'outflow_order__procurement_officer'
        ).filter(
            Q(outflow_order__in=OutflowOrder.objects.filter(
                build_outflow_filter_q(request.query_params, request.organization)
            )),
            warehouse__managers__in=[request.user]
        )

        export_response = None
        if export == 'true':
            if qs.count() == 0:
                export_response = 'No Outbound Orders to Export'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
                }
                process_outflow_export.delay(filter_params, approval=True)
                export_response = 'Export started. You will receive a notification when it is done.'

        qs = qs.order_by('-outflow_order__date_created')

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        serializer = OutflowWarehouseListSerializer(page_obj.object_list, many=True)

        return Response({
            'export_response': export_response,
            'results': serializer.data,
            'pagination': {
                'total': qs.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='verify-availability/(?P<warehouse_id>[^/.]+)')
    @transaction.atomic
    def verify_warehouse_stock(self, request, pk=None, warehouse_id=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
            warehouse_order = order.warehouses.get(id=warehouse_id, is_active=True)
            # Check if the requesting user is a manager of the associated warehouse
            # This ensures that only authorized warehouse managers can verify stock for their assigned warehouses.
            if not warehouse_order.warehouse.managers.filter(pk=request.user.pk).exists():
                return Response(
                    {'error': 'You do not have permission to verify stock for this warehouse.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if warehouse_order.status == 'verified':
                return Response({'error': 'This warehouse has already been verified'},
                                status=status.HTTP_400_BAD_REQUEST)
        except (OutflowOrder.DoesNotExist, OutflowOrderWarehouse.DoesNotExist):
            return Response({'error': 'Outflow Order Not found'}, status=status.HTTP_404_NOT_FOUND)
        except OutflowOrderWarehouse.DoesNotExist:
            return Response({'error': 'Outflow Order Warehouse cannot be found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WarehouseVerificationSerializer(
            warehouse_order,
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_order = serializer.save()

        order_serializer = OutflowOrderApprovalSerializer(updated_order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='mark-order-picked/(?P<warehouse_id>[^/.]+)')
    @transaction.atomic
    def mark_order_picked(self, request, pk=None, warehouse_id=None):
        try:
            order = OutflowOrder.objects.get(pk=pk, organization=request.organization)
            outflow_warehouse = order.warehouses.get(id=warehouse_id, is_active=True)
            # Check if the requesting user is a manager of the associated warehouse
            # This ensures that only authorized warehouse managers can mark orders as picked for their assigned warehouses.
            if not outflow_warehouse.warehouse.managers.filter(pk=request.user.pk).exists():
                return Response(
                    {'error': 'You do not have permission to mark orders as picked for this warehouse.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow order not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OutflowOrderWarehouse.DoesNotExist:
            return Response({'error': 'Outflow order warehouse not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MarkOrderPickedSerializer(
            instance=order,  data=request.data,
            context={'request': request, 'outflow_warehouse':outflow_warehouse,}
        )
        serializer.is_valid(raise_exception=True)
        updated_order = serializer.save()

        response_data = OutflowOrderApprovalSerializer(updated_order, context={'request': request}).data
        return Response(response_data, status=status.HTTP_200_OK)
