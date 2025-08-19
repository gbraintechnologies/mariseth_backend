from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inflow.models import InflowOrder
from apps.inflow.serializers import FullInflowOrderSerializer, InflowOrderSerializer
from apps.shared.literals import LIST_INFLOW_APPROVALS, VIEW_INFLOW_APPROVAL
from apps.shared.utils.permissions import UserPermission


class InflowOrderApprovalViewSet(viewsets.GenericViewSet):
    serializer_class = InflowOrderSerializer
    queryset = InflowOrder.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'retrieve': VIEW_INFLOW_APPROVAL,
            'list': LIST_INFLOW_APPROVALS,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def retrieve(self, request, pk=None):
        try:
            order = InflowOrder.objects.get(pk=pk, is_active=True, organization=request.organization)
            # Check if the requesting user is a manager of the destination warehouse
            if request.user not in order.destination_warehouse.managers.all():
                return Response(
                    {'error': 'You do not have permission to view this inflow order.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return Response(FullInflowOrderSerializer(order).data, status=status.HTTP_200_OK)
        except InflowOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        status_filter = request.query_params.get('status')
        warehouse = request.query_params.get('warehouse')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        query = request.query_params.get('query')
        completed = request.query_params.get('completed', 'false').lower()

        filter_q = Q(is_active=True, organization=request.organization)

        if completed == 'true':
            filter_q &= Q(status='approved')
        else:
            filter_q &= ~Q(status='approved')
        if status_filter:
            filter_q &= Q(status=status_filter)
        if warehouse:
            filter_q &= Q(destination_warehouse=warehouse)
        if start_date and end_date:
            filter_q &= Q(date_created__date__gte=start_date, date_created__date__lte=end_date)
        elif start_date:
            filter_q &= Q(date_created__date__gte=start_date)
        elif end_date:
            filter_q &= Q(date_created__date__lte=end_date)
        if query:
            filter_q &= (
                    Q(order_id__icontains=query) |
                    Q(aggregator__first_name__icontains=query) |
                    Q(aggregator__last_name__icontains=query)
            )

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