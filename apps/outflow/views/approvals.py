from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse
from apps.outflow.serializers.approvals import OutflowOrderApprovalSerializer, WarehouseVerificationSerializer
from apps.shared.utils.permissions import UserPermission


class OutflowApprovalViewSet(viewsets.GenericViewSet):
    queryset = OutflowOrder.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            # 'retrieve': VIEW_OUTFLOW_APPROVAL,
            # 'verify_availability': VERIFY_OUTFLOW_AVAILABILITY,
            # 'mark_order_picked': MARK_OUTFLOW_ORDER_PICKED
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow Order Not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OutflowOrderApprovalSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='verify-availability')
    @transaction.atomic
    def verify_warehouse_stock(self, request, pk=None, warehouse_id=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
            warehouse = order.warehouses.get(id=warehouse_id)
        except (OutflowOrder.DoesNotExist, OutflowOrderWarehouse.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WarehouseVerificationSerializer(
            warehouse,
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = serializer.save()

        # Handle notifications
        # warehouse = result['warehouse']
        # if warehouse.order.warehouses.filter(status='verified').count() == warehouse.order.warehouses.count():
        #     warehouse.order.status = 'truck_pickup'
        #     warehouse.order.save()
        #     send_notification(
        #         group='procurement_officers',
        #         message=f"{warehouse.order.order_id} is ready for truck pickup"
        #     )
        # elif result['has_complaint'] and not result['all_verified']:
        #     send_notification(
        #         group='warehouse_managers',
        #         message=f"{warehouse.order.order_id} has stock shortages in warehouse {warehouse.warehouse.name}"
        #     )

        return Response({'status': 'success', 'warehouse_status': warehouse.status})

    @action(detail=True, methods=['POST'], url_path='mark-order-picked')
    @transaction.atomic
    def mark_order_picked(self, request, pk=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        # only warehouses assigned to this user
        wh = order.warehouses.get(warehouse=request.user.managed_warehouses.first())
        wh.status = 'order_pickup'
        wh.save()

        # notify admin who created
        send_notification(
            recipient=order.procurement_officer,
            message=f"{order.outflow_order_id} picked up by {wh.warehouse.name}"
        )
        return Response(OutflowOrderResponseSerializer(order).data)
