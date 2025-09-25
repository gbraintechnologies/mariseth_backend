import sentry_sdk
from django.core.paginator import Paginator
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import Credit, CreditChangeLog, CreditWarehouse
from apps.credit.serializers.credits import CreditApprovalSerializer, CreditDeleteSerializer, CreditSerializer, \
    CreditWarehouseSerializer, FullCreditSerializer, WarehouseManagerFulfillCreditSerializer
from apps.credit.swagger import add_swagger_to_credit_viewset
from apps.credit.utils import build_credit_filter_q
from apps.shared.literals import APPROVE_OR_DENY_CREDIT, CREATE_CREDIT, DELETE_CREDIT, FULFILL_CREDIT_REQUEST, \
    LIST_CREDITS, LIST_CREDIT_FULFILL, UPDATE_CREDIT, \
    UPLOAD_CREDITS, VIEW_CREDIT, WAREHOUSE_MANAGER_FULFILL_CREDIT
from apps.shared.tasks.export_tasks import process_credit_export
from apps.shared.utils.permissions import UserPermission
from apps.warehouse.models import Warehouse


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
            'fulfill_credit_request': FULFILL_CREDIT_REQUEST,
            'warehouse_manager_fulfill_credit': WAREHOUSE_MANAGER_FULFILL_CREDIT,
            'list_credit_fulfill': LIST_CREDIT_FULFILL,
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
        export = request.query_params.get('export', 'false').lower()

        filter_q = build_credit_filter_q(request.query_params, request.organization)

        queryset = Credit.objects.select_related('farmer').filter(filter_q).order_by('-issue_date')

        export_response = None
        if export == 'true':
            if not queryset.exists():
                export_response = 'No credits to export.'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
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
            return Response({'message': 'Credit deleted successfully'}, status=status.HTTP_200_OK)
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


    @action(detail=True, methods=['POST'], url_path=r'warehouse-fulfill/(?P<warehouse_id>\d+)')
    @transaction.atomic
    def warehouse_manager_fulfill_credit(self, request, pk=None, warehouse_id=None):
        try:
            credit = Credit.objects.get(pk=pk, is_active=True, organization=request.organization)
            warehouse = Warehouse.objects.get(pk=warehouse_id, organization=request.organization)
        except (Credit.DoesNotExist, Warehouse.DoesNotExist):
            return Response({'error': 'Credit or Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WarehouseManagerFulfillCreditSerializer(
            data=request.data,
            context={'request': request, 'credit': credit, 'warehouse': warehouse}
        )
        if serializer.is_valid():
            try:
                credit = serializer.save()

                # Check if credit is now fully fulfilled
                message = f'Credit fulfilled for warehouse {warehouse.name}'
                if credit.is_fulfilled:
                    # TODO: Send notification
                    pass
                return Response({'message': message}, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                sentry_sdk.capture_exception(e)
                return Response({'error': 'An unexpected error occurred.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='warehouse-fulfill-list')
    def list_credit_fulfill(self, request):
        """
        Get a paginated list of warehouse allocations to be fulfilled
        """
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        # Get warehouses managed by the requesting user
        managed_warehouses = request.user.managed_warehouses.all()

        # Get CreditWarehouse entries directly - these are our main objects now
        credit_warehouses_qs = CreditWarehouse.objects.filter(
            warehouse__in=managed_warehouses,
            is_fulfilled=False,
            credit__approval_status='approved',
            credit__payment_status__in=['active', 'partial']
        ).select_related('credit', 'warehouse').order_by('-credit__issue_date')

        paginator = Paginator(credit_warehouses_qs, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': CreditWarehouseSerializer(page_obj.object_list, many=True,
                                                 context={'request': request}).data,
            'pagination': {
                'total': credit_warehouses_qs.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)