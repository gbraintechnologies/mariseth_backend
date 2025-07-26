from django.core.paginator import Paginator
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.models import Expense
from apps.accounting.serializers.expenses import ExpenseSerializer
from apps.shared.literals import LIST_EXPENSES
from apps.shared.utils.permissions import UserPermission


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
        filter_q = Q(is_active=True)

        if order_type:
            filter_q = Q(order_type=order_type)

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
