# views.py
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inflow.models import InflowOrder
from apps.inflow.serializers import DeliveryInspectionApprovalSerializer, FullInflowOrderSerializer, \
    InflowOrderSerializer, \
    OrderApprovalSerializer
from apps.inflow.swagger import add_swagger_to_inflow_viewset
from apps.inflow.utils import build_inflow_filter_q
from apps.shared.literals import APPROVE_INFLOW_DELIVERY_INSPECTION, APPROVE_INFLOW_ORDER, CREATE_INFLOW_ORDER, \
    DELETE_INFLOW_ORDER, LIST_INFLOW_ORDERS, UPDATE_INFLOW_ORDER, VIEW_INFLOW_ORDER
from apps.shared.tasks.export_tasks import process_inflow_export
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_inflow_viewset
class InflowOrderViewSet(viewsets.GenericViewSet):
    serializer_class = InflowOrderSerializer
    queryset = InflowOrder.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_INFLOW_ORDER,
            'update': UPDATE_INFLOW_ORDER,
            'retrieve': VIEW_INFLOW_ORDER,
            'list': LIST_INFLOW_ORDERS,
            'destroy': DELETE_INFLOW_ORDER,
            'approve_inflow_order': APPROVE_INFLOW_ORDER,
            'approve_delivery_inspection': APPROVE_INFLOW_DELIVERY_INSPECTION
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save(organization=request.organization)
            return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(pk=pk, is_active=True, organization=request.organization)
            # Check if the requesting user is a manager of the destination warehouse
            if request.user not in order.destination_warehouse.managers.all():
                return Response(
                    {'error': 'You do not have permission to update this inflow order.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if order.status != "delivery_inspection":
                return Response({'error': 'Order cannot be updated'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(
                instance=order, data=request.data, partial=True, context={'request': request}
            )
            if serializer.is_valid():
                order = serializer.save()
                return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        export = request.query_params.get('export', 'false').lower()
        
        filter_q = build_inflow_filter_q(request.query_params, request.organization)

        orders = InflowOrder.objects.filter(filter_q).order_by("-order_creation_date")

        export_response = None
        if export == 'true':
            if orders.count() == 0:
                export_response = 'No Inbound Orders to Export'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
                }
                process_inflow_export.delay(filter_params)
                export_response = 'Export started. You will receive a notification when it is done.'

        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'export_response': export_response,
            'results': FullInflowOrderSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': orders.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(pk=pk, is_active=True, organization=request.organization)
            # Check if the requesting user is a manager of the destination warehouse
            if request.user not in order.destination_warehouse.managers.all():
                return Response(
                    {'error': 'You do not have permission to delete this inflow order.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if order.status != "delivery_inspection":
                return Response({'error': 'Order cannot be updated'}, status=status.HTTP_400_BAD_REQUEST)
            order.soft_delete(owner=request.user)
            return Response({'message': 'Order deleted successfully'}, status=status.HTTP_200_OK)
        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST'], url_path='approve-delivery-inspection')
    @transaction.atomic
    def approve_delivery_inspection(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(
                pk=pk, is_active=True, organization=request.organization, status='delivery_inspection'
            )
            # Check if the requesting user is a manager of the destination warehouse
            # This ensures that only authorized warehouse managers can approve delivery inspections.
            if request.user not in order.destination_warehouse.managers.all():
                return Response(
                    {'error': 'You do not have permission to approve delivery inspections for this warehouse.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = DeliveryInspectionApprovalSerializer(
                instance=order, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                order = serializer.save()
                return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST'], url_path='approve-order')
    @transaction.atomic
    def approve_order(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(
                pk=pk, is_active=True, organization=request.organization, status='order_approval'
            )
            # Check if the requesting user is a manager of the destination warehouse
            # This ensures that only authorized warehouse managers can approve orders.
            if request.user not in order.destination_warehouse.managers.all():
                return Response(
                    {'error': 'You do not have permission to approve orders for this warehouse.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = OrderApprovalSerializer(
                instance=order, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                order = serializer.save()
                return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
