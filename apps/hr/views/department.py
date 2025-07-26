from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.hr.models import Department
from apps.hr.serializers.department import DepartmentSerializer, FullDepartmentSerializer
from apps.shared.utils.permissions import UserPermission


class DepartmentViewSet(viewsets.GenericViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            # 'create': CREATE_DEPARTMENT,
            # 'update': UPDATE_DEPARTMENT,
            # 'retrieve': VIEW_DEPARTMENT,
            # 'list': LIST_DEPARTMENTS,
            # 'destroy': DELETE_DEPARTMENT,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = DepartmentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        return Response(FullDepartmentSerializer(department).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            department = Department.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullDepartmentSerializer(department).data, status=status.HTTP_200_OK)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            department = Department.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = DepartmentSerializer(department, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            department = serializer.save()
            return Response(FullDepartmentSerializer(department).data, status=status.HTTP_200_OK)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            department = Department.objects.get(pk=pk, is_active=True, organization=request.organization)
            if department.employees.exists():
                return Response({"error": "Cannot delete department with employees"},
                                status=status.HTTP_400_BAD_REQUEST)
            department.soft_delete(owner=request.user)
            return Response({"message": "Department deleted successfully"}, status=status.HTTP_200_OK)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        status_param = request.query_params.get('status')

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= Q(name__icontains=query)
        if status_param:
            filter_q &= Q(status=status_param)

        departments = Department.objects.filter(filter_q).order_by("-date_created")

        paginator = Paginator(departments, page_size)
        page_obj = paginator.get_page(page)

        results = FullDepartmentSerializer(
            instance=page_obj.object_list,
            many=True
        ).data
        return Response(
            {
                'results': results,
                'pagination': {
                    'total': departments.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )
