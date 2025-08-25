from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.hr.models import Employee, EmployeeQualification, LeaveRequest, TrainingAttendee
from apps.hr.serializers.employee import DisciplinaryActionSerializer, EmployeeSerializer, FullEmployeeSerializer, \
    ListEmployeeSerializer, QualificationSerializer
from apps.hr.utils import build_employee_filter_q
from apps.hr.serializers.leave import ListEmployeeLeaveRequestSerializer
from apps.hr.serializers.training import ListTrainingAttendeeSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import (ADD_EMPLOYEE_DISCIPLINARY_ACTION, ADD_EMPLOYEE_QUALIFICATION, CREATE_EMPLOYEE,
                                  DELETE_EMPLOYEE, LIST_EMPLOYEES, LIST_EMPLOYEE_DISCIPLINARY_ACTIONS,
                                  LIST_LEAVE_REQUESTS, LIST_TRAININGS, REMOVE_EMPLOYEE_QUALIFICATION, UPDATE_EMPLOYEE,
                                  VIEW_EMPLOYEE)
from apps.shared.utils.permissions import UserPermission
from apps.shared.tasks.export_tasks import process_employee_export

class EmployeeViewSet(viewsets.GenericViewSet):
    queryset = Employee.objects.filter(is_active=True)
    serializer_class = EmployeeSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_EMPLOYEE,
            'update': UPDATE_EMPLOYEE,
            'retrieve': VIEW_EMPLOYEE,
            'list': LIST_EMPLOYEES,
            'destroy': DELETE_EMPLOYEE,
            'add_qualification': ADD_EMPLOYEE_QUALIFICATION,
            'remove_qualification': REMOVE_EMPLOYEE_QUALIFICATION,
            'disciplinary_action': ADD_EMPLOYEE_DISCIPLINARY_ACTION,
            'disciplinary_actions': LIST_EMPLOYEE_DISCIPLINARY_ACTIONS,
            'get_employee_trainings': LIST_TRAININGS,
            'get_employee_leave_requests': LIST_LEAVE_REQUESTS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = EmployeeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(FullEmployeeSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = self.get_serializer(employee, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(FullEmployeeSerializer(serializer.instance).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullEmployeeSerializer(employee).data, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        export = request.query_params.get('export', 'false').lower()
        filter_q = build_employee_filter_q(request.query_params, request.organization)

        employees = Employee.objects.filter(filter_q).order_by('-date_created')
        export_response = None
        if export == 'true':
            if employees.count() == 0:
                export_response = 'No farms to export'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
                }
                process_employee_export.delay(filter_params)
                export_response = 'Export started. You will receive a notification when it is done.'

        paginator = Paginator(employees, page_size)
        page_obj = paginator.get_page(page)

        results = ListEmployeeSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'export_response': export_response,
            'results': results,
            'pagination': {
                'total': employees.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            employee.soft_delete(owner=request.user, fields_to_encrypt=['phone_number', 'email'])
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST'], url_path='add-qualification')
    @transaction.atomic
    def add_qualification(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = QualificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employee=employee)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='remove-qualification/(?P<qualification_id>[^/.]+)')
    @transaction.atomic
    def remove_qualification(self, request, pk=None, qualification_id=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            qualification = employee.qualifications.get(pk=qualification_id)
            qualification.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        except EmployeeQualification.DoesNotExist:
            return Response({'error': 'Qualification not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST'], url_path='disciplinary-action')
    @transaction.atomic
    def disciplinary_action(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            request.data['employee'] = employee
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = DisciplinaryActionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(employee=employee)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['GET'], url_path='disciplinary-actions')
    def disciplinary_actions(self, request, pk=None):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True, organization=request.organization)
            disciplinary_actions = employee.disciplinary_actions.filter(is_active=True)
            serializer = DisciplinaryActionSerializer(disciplinary_actions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['GET'], url_path='trainings')
    def get_employee_trainings(self, request, pk=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        filter_q = Q(employee__id=pk, is_active=True)
        training = TrainingAttendee.objects.filter(filter_q).order_by('-date_created')

        paginator = Paginator(training, page_size)
        page_obj = paginator.get_page(page)

        results = ListTrainingAttendeeSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'results': results,
            'pagination': {
                'total': training.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], url_path='leave-requests')
    def get_employee_leave_requests(self, request, pk=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        filter_q = Q(employee__id=pk, is_active=True, organization=request.organization)
        leave = LeaveRequest.objects.filter(filter_q).order_by('-date_created')

        paginator = Paginator(leave, page_size)
        page_obj = paginator.get_page(page)

        results = ListEmployeeLeaveRequestSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'results': results,
            'pagination': {
                'total': leave.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)