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
from apps.shared.literals import APPROVE_INFLOW_DELIVERY_INSPECTION, APPROVE_INFLOW_ORDER, CREATE_INFLOW_ORDER, \
    DELETE_INFLOW_ORDER, LIST_INFLOW_ORDERS, UPDATE_INFLOW_ORDER, VIEW_INFLOW_ORDER
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
        status_filter = request.query_params.get('status')
        warehouse = request.query_params.get('warehouse')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        query = request.query_params.get('query')
        export = request.query_params.get('export', 'false').lower()

        filter_q = Q(is_active=True, organization=request.organization)

        if status_filter:
            filter_q &= Q(status=status_filter)
        if warehouse:
            filter_q &= Q(destination_warehouse=warehouse)
        if date_from and date_to:
            filter_q &= Q(order_creation_date__range=[date_from, date_to])
        if query:
            filter_q &= (
                    Q(order_id__icontains=query) |
                    Q(comments__icontains=query)
            )

        if export == 'true':
            pass
        # TOD0: ADD AN EXPORT BACKGROUND TASK

        orders = InflowOrder.objects.filter(filter_q).order_by("-order_creation_date")

        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)

        return Response({
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
            serializer = OrderApprovalSerializer(
                instance=order, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                order = serializer.save()
                return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
