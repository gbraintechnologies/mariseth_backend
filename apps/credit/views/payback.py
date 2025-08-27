from django.core.paginator import Paginator
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import CreditPayback
from apps.credit.serializers.payback import CreditPaybackSerializer, FullPaybackSerializer
from apps.credit.swagger import add_swagger_to_payback_viewset
from apps.credit.utils import build_payback_filter_q
from apps.shared.literals import CREATE_PAYBACK, LIST_PAYBACKS, UPDATE_PAYBACK
from apps.shared.tasks.export_tasks import process_payback_export
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
        export = request.query_params.get('export', 'false').lower()

        filter_q = build_payback_filter_q(request.query_params, request.organization)
        paybacks = CreditPayback.objects.filter(filter_q).order_by('-date_created')

        export_response = None
        if export == 'true':
            if paybacks.count() == 0:
                export_response = 'No paybacks to export'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
                }
                process_payback_export.delay(filter_params)
                export_response = 'Export started. You will receive a notification when it is done.'

        paginator = Paginator(paybacks, page_size)
        page_obj = paginator.get_page(page)

        results = FullPaybackSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'export_response': export_response,
            'results': results,
            'pagination': {
                'total': paybacks.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
