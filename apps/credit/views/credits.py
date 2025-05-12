from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import Credit
from apps.credit.serializers.credits import CreditApprovalSerializer, CreditDeleteSerializer, CreditSerializer, \
    FullCreditSerializer
from apps.credit.swagger import add_swagger_to_credit_viewset
from apps.shared.literals import APPROVE_OR_DENY_CREDIT, CREATE_CREDIT, DELETE_CREDIT, LIST_CREDITS, UPDATE_CREDIT, \
    UPLOAD_CREDITS, VIEW_CREDIT
from apps.shared.tasks.export_tasks import process_credit_export
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_credit_viewset
class CreditViewSet(viewsets.GenericViewSet):
    serializer_class = CreditSerializer
    queryset = Credit.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_CREDIT,
            'update': UPDATE_CREDIT,
            'retrieve': VIEW_CREDIT,
            'list': LIST_CREDITS,
            'destroy': DELETE_CREDIT,
            'upload_credits': UPLOAD_CREDITS,
            'approve_deny_credit': APPROVE_OR_DENY_CREDIT,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = CreditSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            credit = serializer.save()
            return Response(FullCreditSerializer(credit).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            credit = Credit.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = CreditSerializer(credit, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                credit = serializer.save()
                return Response(FullCreditSerializer(credit).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Credit.DoesNotExist:
            return Response({'error': 'Credit not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            credit = Credit.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullCreditSerializer(credit).data)
        except Credit.DoesNotExist:
            return Response({'error': 'Credit not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        payment_status = request.query_params.get('payment_status')
        farmer = request.query_params.get('farmer')
        input_type = request.query_params.get('input_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        export = request.query_params.get('export', 'false').lower()

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (
                    Q(id__icontains=query) |
                    Q(farmer__first_name__icontains=query) |
                    Q(farmer__last_name__icontains=query)
            )

        if payment_status:
            filter_q &= Q(payment_status=payment_status.lower())

        if input_type:
            filter_q &= Q(type=input_type.lower())

        if date_from and date_to:
            filter_q &= Q(issue_date__range=[date_from, date_to])

        if farmer:
            filter_q &= Q(farmer__id=farmer)

        queryset = Credit.objects.select_related('farmer').filter(filter_q).order_by('-issue_date')

        export_response = None
        if export == 'true':
            filter_params = {
                'user_id': request.user.id,
                'organization_id': request.organization.id,
                'query': query,
                'payment_status': payment_status,
                'input_type': input_type,
                'date_from': date_from,
                'date_to': date_to
            }
            process_credit_export.delay(filter_params)
            export_response = 'Export started. You will receive a notification when it is done.'

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'export_response': export_response,
            'results': FullCreditSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            credit = Credit.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = CreditDeleteSerializer(credit, data=request.data, context={'request': request})
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            credit.soft_delete(deleted_by=request.user)
            return Response({'message': 'Credit deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Credit.DoesNotExist:
            return Response({'error': 'Credit not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST'], url_path='upload-credits')
    def upload_credits(self, request):
        # Implement CSV upload logic
        return Response({'message': 'CSV upload endpoint'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='approve-deny-credit')
    @transaction.atomic
    def approve_deny_credit(self, request, pk=None):
        try:
            credit = Credit.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Credit.DoesNotExist:
            return Response({'error': 'Credit not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreditApprovalSerializer(data=request.data, context={'credit': credit, 'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            credit = serializer.save()
            return Response(FullCreditSerializer(credit).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
