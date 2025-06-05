from datetime import datetime

from django.db.models import Count, Q, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farmer
from apps.shared.literals import LIST_FARMERS
from apps.shared.swagger import add_swagger_to_dashboard_viewset
from apps.shared.utils.permissions import UserPermission
from apps.warehouse.models import Warehouse


@add_swagger_to_dashboard_viewset
class DashboardViewSet(viewsets.ModelViewSet):

    def get_permissions(self):
        permissions = {
            'farmer_analysis': LIST_FARMERS,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @action(detail=False, methods=['GET'], url_path='farmer-analysis')
    def farmer_analysis(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        base_farmer_queryset = Farmer.objects.filter(is_active=True, date_deleted__isnull=True)
        base_warehouse_queryset = Warehouse.objects.filter(is_active=True, date_deleted__isnull=True)
        date_filter = Q(is_active=True)
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                if start_date > end_date:
                    return Response(
                        {"error": "start_date cannot be after end_date."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                date_filter = Q(date_created__date__gte=start_date, date_created__date__lte=end_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Please use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        farmer_queryset = base_farmer_queryset.filter(date_filter)
        warehouse_queryset = base_warehouse_queryset.filter(date_filter)
        farmer_stats = farmer_queryset.aggregate(
            total_lead_farmers=Coalesce(Count('pk', filter=Q(type='lead')), Value(0)),
            total_smallholder_farmers=Coalesce(Count('pk', filter=Q(type='smallholder')), Value(0)),
            total_male_farmers=Coalesce(Count('pk', filter=Q(gender='m')), Value(0)),
            total_female_farmers=Coalesce(Count('pk', filter=Q(gender='f')), Value(0))
        )
        active_warehouses_count = warehouse_queryset.count()
        response_data = {
            "lead_farmers": farmer_stats['total_lead_farmers'],
            "smallholder_farmers": farmer_stats['total_smallholder_farmers'],
            "active_warehouses": active_warehouses_count,
            "gender_distribution": {
                "male": farmer_stats['total_male_farmers'],
                "female": farmer_stats['total_female_farmers']
            },
            "distribution_by_farmer_type": {
                "lead_farmer": farmer_stats['total_lead_farmers'],
                "smallholder_farmer": farmer_stats['total_smallholder_farmers']
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
