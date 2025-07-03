from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse
from apps.outflow.serializers.outflow import (
    FullOutflowOrderSerializer, ListOutflowOrderSerializer, OutflowOrderDeliveryInformationSerializer,
    OutflowOrderPaymentRequestSerializer, OutflowOrderSerializer
)
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import ASSIGN_DELIVERY_INFO, CREATE_OUTFLOW_ORDER, DELETE_OUTFLOW_ORDER, LIST_OUTFLOW_ORDERS, \
    MARK_OUTFLOW_COMPLETE, MARK_OUTFLOW_DELIVERED, RECORD_OUTFLOW_PAYMENT, UPDATE_OUTFLOW_ORDER, \
    VIEW_OUTFLOW_ORDER
from apps.shared.utils.permissions import UserPermission


class OutflowOrderViewSet(viewsets.GenericViewSet):
    queryset = OutflowOrder.objects.filter(is_active=True)
    serializer_class = OutflowOrderSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_OUTFLOW_ORDER,
            'update': UPDATE_OUTFLOW_ORDER,
            'retrieve': VIEW_OUTFLOW_ORDER,
            'list': LIST_OUTFLOW_ORDERS,
            'destroy': DELETE_OUTFLOW_ORDER,
            'assign_delivery_info': ASSIGN_DELIVERY_INFO,
            'mark_delivered': MARK_OUTFLOW_DELIVERED,
            'record_payment': RECORD_OUTFLOW_PAYMENT,
            'mark_complete': MARK_OUTFLOW_COMPLETE,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = OutflowOrderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response(FullOutflowOrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            order = OutflowOrder.objects.get(pk=pk, is_active=True, organization=request.organization)
            if order.status not in ['availability_check', 'pending']:
                return Response({'error': 'Order cannot be modified in current state'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = OutflowOrderSerializer(instance=order, data=request.data, partial=True,
                                                context={'request': request})
            if serializer.is_valid():
                updated_order = serializer.save()
                return Response(FullOutflowOrderSerializer(updated_order).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow Order not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FullOutflowOrderSerializer(order).data)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        status_filter = request.query_params.get('status')
        query = request.query_params.get('query')
        completed = request.query_params.get('completed', 'false').lower()
        export = request.query_params.get('export', 'false').lower()

        filter_q = Q(is_active=True, organization=request.organization)
        if completed == 'true':
            filter_q &= Q(status='complete')
        else:
            filter_q &= ~Q(status='complete')
        if status_filter:
            filter_q &= Q(status=status_filter)
        if query:
            filter_q &= (
                    Q(order_id__icontains=query) |
                    Q(destination__name__icontains=query)
            )

        orders = OutflowOrder.objects.filter(filter_q).order_by("-date_created")

        # Export placeholder
        if export == 'true':
            pass  # TODO: ADD AN EXPORT BACKGROUND TASK

        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': ListOutflowOrderSerializer(page_obj.object_list, many=True).data,
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
            order = OutflowOrder.objects.get(id=pk, organization=request.organization, is_active=True)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        order.soft_delete(owner=request.user)
        for warehouse in OutflowOrderWarehouse.objects.filter(outflow_order=order, is_active=True):
            warehouse.soft_delete(owner=request.user)
            for product in warehouse.products.filter(is_active=True):
                product.soft_delete(owner=request.user)

        return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='assign-delivery-info')
    @transaction.atomic
    def assign_delivery_info(self, request, pk=None):
        try:
            order = OutflowOrder.objects.get(pk=pk, organization=request.organization, is_active=True)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OutflowOrderDeliveryInformationSerializer(
            data=request.data,
            many=True,
            context={'request': request, 'order': order}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        delivery_info = serializer.save()

        return Response(FullOutflowOrderSerializer(order).data, status=status.HTTP_201_CREATED)  # response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'], url_path='mark-delivered')
    @transaction.atomic
    def mark_delivered(self, request, pk=None):
        try:
            order = OutflowOrder.objects.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'truck_pickup':
            return Response(
                {'error': 'Order can only be marked as delivered after truck pickup'},
                status=status.HTTP_400_BAD_REQUEST
            )
        old_status = order.status
        order.status = 'delivered'
        order.actual_delivery_date = timezone.now().date()
        order.save()
        order.log_status_change(old_status, 'delivered', request.user)
        serializer = FullOutflowOrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='record-payment')
    @transaction.atomic
    def record_payment(self, request, pk=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow order not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OutflowOrderPaymentRequestSerializer(
            data=request.data,
            context={'order': order, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = FullOutflowOrderSerializer(order).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'], url_path='mark-complete')
    @transaction.atomic
    def mark_complete(self, request, pk=None):
        try:
            order = self.queryset.get(pk=pk, organization=request.organization)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'full_payment':
            return Response({'error': 'Order must be fully paid before completion.'},
                            status=status.HTTP_400_BAD_REQUEST)
        old_status = order.status
        order.status = 'complete'
        order.save()
        order.log_status_change( old_status, 'complete',request.user)
        serializer = FullOutflowOrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


