from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.hr.models import LeaveRequest, LeaveType
from apps.hr.serializers.leave import ApproveDeclineLeaveRequestSerializer, FullLeaveRequestSerializer, \
    LeaveRequestSerializer, LeaveTypeSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import (
    APPROVE_DECLINE_LEAVE_REQUEST, CREATE_LEAVE_REQUEST, CREATE_LEAVE_TYPE,
    DELETE_LEAVE_REQUEST, DELETE_LEAVE_TYPE, LIST_LEAVE_REQUESTS, LIST_LEAVE_TYPES,
    UPDATE_LEAVE_REQUEST, UPDATE_LEAVE_TYPE, VIEW_LEAVE_REQUEST
)
from apps.shared.utils.permissions import UserPermission


class LeaveTypeViewSet(viewsets.GenericViewSet):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_LEAVE_TYPE,
            'update': UPDATE_LEAVE_TYPE,
            'list': LIST_LEAVE_TYPES,
            'destroy': DELETE_LEAVE_TYPE,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = LeaveTypeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(organization=request.organization, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            leave_type = LeaveType.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = LeaveTypeSerializer(
                instance=leave_type, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                leave_type = serializer.save()
                return Response(LeaveTypeSerializer(leave_type).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LeaveType.DoesNotExist:
            return Response({'error': 'LeaveType not found'}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            leave_type = LeaveType.objects.get(pk=pk, is_active=True, organization=request.organization)
            if leave_type.leave_requests.exists():
                return Response({'error': 'Leave type has associated leave requests'},
                                status=status.HTTP_400_BAD_REQUEST)
            leave_type.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except LeaveType.DoesNotExist:
            return Response({'error': 'Leave Type not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        organization = request.organization
        leave_types = LeaveType.objects.filter(is_active=True, organization=organization)
        return Response(
            LeaveTypeSerializer(instance=leave_types, many=True).data, status=status.HTTP_200_OK
        )


class LeaveRequestViewSet(viewsets.GenericViewSet):
    queryset = LeaveRequest.objects.filter(is_active=True)
    serializer_class = LeaveRequestSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_LEAVE_REQUEST,
            'retrieve': VIEW_LEAVE_REQUEST,
            'update': UPDATE_LEAVE_REQUEST,
            'list': LIST_LEAVE_REQUESTS,
            'destroy': DELETE_LEAVE_REQUEST,
            'approve_decline': APPROVE_DECLINE_LEAVE_REQUEST,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = LeaveRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(FullLeaveRequestSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = LeaveRequestSerializer(instance, data=request.data, partial=partial, context={'request': request})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            leave = LeaveRequest.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = LeaveRequestSerializer(
                leave, data=request.data, partial=True, context={'request': request}
            )
            if serializer.is_valid():
                leave = serializer.save()
                leave.employee.contract.refresh_from_db()
                return Response(FullLeaveRequestSerializer(leave).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave Request not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, *args, **kwargs):
        try:
            leave_request = LeaveRequest.objects.get(pk=kwargs['pk'], is_active=True, organization=request.organization)
            serializer = FullLeaveRequestSerializer(leave_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        leave_type = request.query_params.get('leave_type')
        status_param = request.query_params.get('status')
        department = request.query_params.get('department')
        query = request.query_params.get('query')
        completed = request.query_params.get('completed')

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (
                Q(employee__first_name__icontains=query) |
                Q(employee__last_name__icontains=query) |
                Q(employee__employee_id__icontains=query) |
                Q(employee__email__icontains=query) |
                Q(employee__phone_number__icontains=query)
            )

        if leave_type:
            filter_q &= Q(leave_type=leave_type)
        if status_param:
            filter_q &= Q(status=status_param)
        if department:
            filter_q &= Q(employee__contract__department__id=department)

        queryset = LeaveRequest.objects.filter(filter_q).order_by('-date_created')

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        results = FullLeaveRequestSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'results': results,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            leave = LeaveRequest.objects.get(pk=pk, is_active=True, organization=request.organization)
            if leave.status not in ['pending', 'declined']:
                return Response({'error': 'Leave Request cannot be deleted.'},
                                status=status.HTTP_400_BAD_REQUEST)
            leave.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave Request not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='approve-decline')
    @transaction.atomic
    def approve_decline(self, request, pk=None):
        try:
            leave_request = LeaveRequest.objects.get(pk=pk, is_active=True, employee__organization=request.organization)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApproveDeclineLeaveRequestSerializer(
            instance=leave_request,
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        leave = serializer.save()
        return Response(FullLeaveRequestSerializer(leave).data, status=status.HTTP_200_OK)
