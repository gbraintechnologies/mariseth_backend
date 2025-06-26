from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse
from apps.outflow.serializers.approvals import MarkOrderPickedSerializer, OutflowOrderApprovalSerializer, \
    WarehouseVerificationSerializer
from apps.shared.literals import MARK_OUTFLOW_ORDER_PICKED, VERIFY_OUTFLOW_AVAILABILITY, VIEW_OUTFLOW_APPROVAL
from apps.shared.utils.permissions import UserPermission


class OutflowApprovalViewSet(viewsets.GenericViewSet):
    queryset = OutflowOrder.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'retrieve': VIEW_OUTFLOW_APPROVAL,
            'verify_availability': VERIFY_OUTFLOW_AVAILABILITY,
            'mark_order_picked': MARK_OUTFLOW_ORDER_PICKED
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        """
            Retrieves a single outflow order for approval, visible to warehouse managers.

            This endpoint allows an authenticated warehouse manager to view the details
            of a specific outflow order. The order details include information about
            the customer, procurement officer, destination, expected delivery date,
            overall status, and aggregated total quantity and cost. Crucially, it
            also provides a breakdown of products by warehouse, specifically
            filtering to include only those warehouses managed by the requesting user.
        """
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow Order Not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OutflowOrderApprovalSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='verify-availability/(?P<warehouse_id>[^/.]+)')
    @transaction.atomic
    def verify_warehouse_stock(self, request, pk=None, warehouse_id=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
            warehouse = order.warehouses.get(id=warehouse_id, is_active=True)
            if warehouse.status == 'verified':
                return Response({'error': 'This warehouse has already been verified'},
                                status=status.HTTP_400_BAD_REQUEST)
        except (OutflowOrder.DoesNotExist, OutflowOrderWarehouse.DoesNotExist):
            return Response({'error': 'Outflow Order Not found'}, status=status.HTTP_404_NOT_FOUND)
        except OutflowOrderWarehouse.DoesNotExist:
            return Response({'error': 'Outflow Order Warehouse cannot be found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WarehouseVerificationSerializer(
            warehouse,
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
