from django.core.paginator import Paginator
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.models import Expense
from apps.accounting.serializers.expenses import ExpenseSerializer
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder
from apps.shared.literals import LIST_EXPENSES
from apps.shared.utils.permissions import UserPermission
from django.contrib.contenttypes.models import ContentType


class ExpenseViewSet(viewsets.GenericViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def get_permissions(self):
        permissions = {
            'list': LIST_EXPENSES,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        order_type = request.query_params.get('order_type')
        query = request.query_params.get('query')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        filter_q = Q(is_active=True)

        if order_type:
            filter_q = Q(order_type=order_type)
        if query:
            inflow_ct = ContentType.objects.get_for_model(InflowOrder)
            outflow_ct = ContentType.objects.get_for_model(OutflowOrder)

            inflow_ids = InflowOrder.objects.filter(order_id__icontains=query).values_list('id', flat=True)
            outflow_ids = OutflowOrder.objects.filter(order_id__icontains=query).values_list('id', flat=True)

            filter_q &= (
                    Q(content_type=inflow_ct, object_id__in=inflow_ids) |
                    Q(content_type=outflow_ct, object_id__in=outflow_ids)
            )
        if start_date and end_date:
            filter_q &= Q(date_created__date__range=[start_date, end_date])

        expenses = Expense.objects.filter(filter_q).order_by('-date_created')
        total_expenses = expenses.aggregate(total_sum=Sum('amount'))

        paginator = Paginator(expenses, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'total_expenses': total_expenses,
            'results': ExpenseSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': expenses.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
