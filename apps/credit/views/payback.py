from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import CreditPayback
from apps.credit.serializers.payback import CreditPaybackSerializer, FullPaybackSerializer
from apps.credit.swagger import add_swagger_to_payback_viewset
from apps.shared.literals import CREATE_PAYBACK, LIST_PAYBACKS, UPDATE_PAYBACK
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_payback_viewset
class PaybackViewSet(viewsets.GenericViewSet):
    serializer_class = CreditPaybackSerializer
    queryset = CreditPayback.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_PAYBACK,
            'update': UPDATE_PAYBACK,
            'list': LIST_PAYBACKS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = CreditPaybackSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(FullPaybackSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            payback = CreditPayback.objects.get(pk=pk, is_active=True)
        except CreditPayback.DoesNotExist:
            return Response({'error': 'Payback not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CreditPaybackSerializer(payback, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(FullPaybackSerializer(serializer.instance).data, status=status.HTTP_200_OK)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        credit_id = request.query_params.get('credit')
        payback_method = request.query_params.get('payback_method')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        filters = Q(credit__organization=request.organization, is_active=True)

        if credit_id:
            filters &= Q(credit_id=credit_id)
        if payback_method:
            filters &= Q(payback_method=payback_method)
        if start_date and end_date:
            filters &= Q(date_paid__range=[start_date, end_date])
        if status_filter:
            filters &= Q(status=status_filter)

        queryset = CreditPayback.objects.filter(filters).order_by("-date_created")

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullPaybackSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
