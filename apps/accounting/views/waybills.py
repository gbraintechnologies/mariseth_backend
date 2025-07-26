from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.serializers.waybills import InflowOrderListRetrieveSerializer, OutflowOrderListRetrieveSerializer
from apps.inflow.models import InflowOrder
from apps.inflow.serializers import FullInflowOrderSerializer
from apps.outflow.models import OutflowOrder
from apps.outflow.serializers.outflow import FullOutflowOrderSerializer
from apps.shared.literals import LIST_WAYBILLS, VIEW_WAYBILL
from apps.shared.utils.permissions import UserPermission


class WaybillViewSet(viewsets.ViewSet):
    queryset = InflowOrder.objects.all()
    serializer_class = InflowOrderListRetrieveSerializer

    def get_permissions(self):
        permissions = {
            'list': LIST_WAYBILLS,
            'retrieve': VIEW_WAYBILL
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        order_type = request.query_params.get('order_type', 'inflow')

        if order_type == 'inflow':
            queryset = InflowOrder.objects.filter(is_active=True)
            serializer_class = InflowOrderListRetrieveSerializer
        elif order_type == 'outflow':
            queryset = OutflowOrder.objects.filter(is_active=True)
            serializer_class = OutflowOrderListRetrieveSerializer
        else:
            return Response({'error': 'order_type parameter is required (inflow or outflow).'},
                            status=status.HTTP_400_BAD_REQUEST)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = serializer_class(page_obj.object_list, many=True)

        return Response({
            'results': serializer.data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        order_type = request.query_params.get('order_type')

        if order_type == 'inflow':
            queryset = InflowOrder.objects.all()
            order = get_object_or_404(queryset, pk=pk)
            serializer = FullInflowOrderSerializer(order)
        elif order_type == 'outflow':
            queryset = OutflowOrder.objects.filter(is_active=True)
            order = get_object_or_404(queryset, pk=pk)
            serializer = FullOutflowOrderSerializer(order)
        else:
            return Response({'error': 'order_type parameter is required (inflow or outflow).'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data)
