from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inflow.models import InflowOrderHistory
from apps.outflow.models import OutflowOrderHistory
from apps.shared.literals import LIST_INFLOW_HISTORY, LIST_OUTFLOW_HISTORY
from apps.shared.serializers.audit_trail import InflowOrderHistorySerializer, OutflowOrderHistorySerializer
from apps.shared.utils.permissions import UserPermission


class AuditTrailViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        permissions = {
            'list_outflow_history': LIST_OUTFLOW_HISTORY,
            'list_inflow_history': LIST_INFLOW_HISTORY,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='outflow')
    def list_outflow_history(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query', None)
        organization = request.organization

        queryset = OutflowOrderHistory.objects.filter(
            outflow_order__organization=organization
        ).order_by('-id')

        if query:
            queryset = queryset.filter(
                field_name__icontains=query
            ) | queryset.filter(
                old_value__icontains=query
            ) | queryset.filter(
                new_value__icontains=query
            )

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        results = OutflowOrderHistorySerializer(
            instance=page_obj.object_list,
            many=True
        ).data

        return Response(
            {
                'results': results,
                'pagination': {
                    'total': queryset.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='inflow')
    def list_inflow_history(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query', None)
        organization = request.organization

        queryset = InflowOrderHistory.objects.filter(
            order__organization=organization
        ).order_by('-id')

        if query:
            queryset = queryset.filter(
                notes__icontains=query
            ) | queryset.filter(
                old_value__icontains=query
            ) | queryset.filter(
                new_value__icontains=query
            ) | queryset.filter(
                field_name__icontains=query
            )

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        results = InflowOrderHistorySerializer(
            instance=page_obj.object_list,
            many=True
        ).data

        return Response(
            {
                'results': results,
                'pagination': {
                    'total': queryset.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )
