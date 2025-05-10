from calendar import monthcalendar
from collections import OrderedDict
from datetime import date, datetime, timedelta

from django.db.models import Case, Count, DecimalField, Q, Sum, When
from django.db.models.functions import Trunc
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.shared.literals import VIEW_DIVIDEND_ANALYSIS, VIEW_SHAREHOLDER_ANALYSIS
from apps.shared.utils.permissions import UserPermission
from apps.shareholders.models import Shareholder, ShareholderPayout


class ShareholderDistributionSerializer(serializers.Serializer):
    individual = serializers.IntegerField()
    company = serializers.IntegerField()
    group = serializers.IntegerField()


class ShareholderCardSerializer(serializers.Serializer):
    total_shareholders = serializers.IntegerField()
    new_shareholders = serializers.IntegerField()
    total_shares = serializers.DecimalField(max_digits=15, decimal_places=2)
    shareholder_distribution = ShareholderDistributionSerializer()


class PayoutCardSerializer(serializers.Serializer):
    received_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    due_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class DashboardViewSet(viewsets.ModelViewSet):

    def get_permissions(self):
        permissions = {
          'shareholder_analysis': VIEW_SHAREHOLDER_ANALYSIS,
          'dividend_analysis': VIEW_DIVIDEND_ANALYSIS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='shareholder-analysis')
    def shareholder_analysis(self, request):
        """Retrieves shareholder card data for the given organization."""
        organization = request.organization

        if not organization:
            return Response({"error": "Organization not found in request."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Shareholder.objects.filter(organization=organization, is_active=True)

        total_shareholders = queryset.count()
        new_shareholders = queryset.filter(date_created__gte=datetime.now() - timedelta(days=7)).count()
        total_shares = queryset.aggregate(total_shares=Sum('number_of_shares'))['total_shares'] or 0

        distribution_data = queryset.aggregate(
            individual=Count('id', filter=Q(entity_type='individual')),
            company=Count('id', filter=Q(entity_type='company')),
            group=Count('id', filter=Q(entity_type='organized_group')),
        )

        data = {
            'total_shareholders': total_shareholders,
            'new_shareholders': new_shareholders,
            'total_shares': total_shares,
            'shareholder_distribution': distribution_data,
        }

        serializer = ShareholderCardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='dividend-analysis')
    def dividend_analysis(self, request):
        organization = request.organization
        if not organization:
            return Response({'error': 'Organization not found in request.'}, status=status.HTTP_400_BAD_REQUEST)

        time_period = request.query_params.get('time_period', 'monthly').lower()
        valid_time_periods = ['daily', 'weekly', 'monthly', 'yearly']
        if time_period not in valid_time_periods:
            raise ParseError(detail='Invalid time period. Must be "daily", "weekly", "monthly", or "yearly".')

        now = timezone.now().date()
        current_year = now.year
        current_month = now.month

        if time_period == 'daily':
            date_range = [now - timedelta(days=i) for i in range(7)]
            date_format = '%Y-%m-%d'
            trunc_type = 'day'

        elif time_period == 'weekly':
            cal = monthcalendar(current_year, current_month)
            date_range = []
            for week_days in cal:
                valid_days = [day for day in week_days if day != 0]
                if valid_days:
                    monday = date(current_year, current_month, valid_days[0])
                    date_range.append(monday)
            date_format = '%Y-%m-%d'
            trunc_type = 'week'

        elif time_period == 'monthly':
            date_range = [
                date(current_year - (1 if current_month + m > 12 else 0),
                     (current_month + m - 1) % 12 + 1,
                     1)
                for m in range(-11, 1)
            ]
            date_format = '%Y-%m'
            trunc_type = 'month'

        elif time_period == 'yearly':
            start_year = current_year - 1
            first_payout = ShareholderPayout.objects.filter(
                shareholder__organization=organization
            ).order_by('date').first()
            min_year = max(first_payout.date.year if first_payout else current_year, start_year)
            date_range = [date(y, 1, 1) for y in range(min_year, current_year + 1)]
            date_format = '%Y'
            trunc_type = 'year'

        else:
            return Response({'error': 'Invalid time period'}, status=status.HTTP_400_BAD_REQUEST)

        # Single-query approach using Case/When for summations. This avoids multiple DB hits.
        queryset = (
            ShareholderPayout.objects
            .filter(
                shareholder__organization=organization,
                date__gte=date_range[0] if date_range else now,
                is_active=True
            )
            .annotate(period=Trunc('date', trunc_type))
            .values('period')
            .annotate(
                received_amount=Sum(
                    Case(
                        When(status='complete', then='amount'),
                        default=0,
                        output_field=DecimalField()
                    )
                ),
                due_amount=Sum(
                    Case(
                        When(status='pending_approval', then='amount'),
                        default=0,
                        output_field=DecimalField()
                    )
                )
            )
            .order_by('period')
        )

        # Convert queryset into a dict keyed by formatted period
        data_dict = {}
        for item in queryset:
            formatted_period = item['period'].strftime(date_format)
            data_dict[formatted_period] = {
                'received_amount': item['received_amount'],
                'due_amount': item['due_amount'],
            }

        result = OrderedDict()
        for d in date_range:
            formatted_date = d.strftime(date_format)
            result[formatted_date] = {
                'received_amount': data_dict.get(formatted_date, {}).get('received_amount', 0),
                'due_amount': data_dict.get(formatted_date, {}).get('due_amount', 0),
            }

        return Response(result, status=status.HTTP_200_OK)

