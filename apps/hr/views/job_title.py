from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.hr.models import JobTitle
from apps.hr.serializers.job_title import FullJobTitleSerializer, JobTitleSerializer
from apps.shared.literals import (
    CREATE_JOB_TITLE, DELETE_JOB_TITLE, LIST_JOB_TITLES, UPDATE_JOB_TITLE, VIEW_JOB_TITLE,
)
from apps.shared.utils.permissions import UserPermission


class JobTitleViewSet(viewsets.GenericViewSet):
    serializer_class = JobTitleSerializer
    queryset = JobTitle.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_JOB_TITLE,
            'update': UPDATE_JOB_TITLE,
            'retrieve': VIEW_JOB_TITLE,
            'list': LIST_JOB_TITLES,
            'destroy': DELETE_JOB_TITLE,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = JobTitleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        job_title = serializer.save()
        return Response(FullJobTitleSerializer(job_title).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            job_title = JobTitle.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullJobTitleSerializer(job_title).data, status=status.HTTP_200_OK)
        except JobTitle.DoesNotExist:
            return Response({"error": "Job Title not found"}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            job_title = JobTitle.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = JobTitleSerializer(job_title, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            job_title = serializer.save()
            return Response(FullJobTitleSerializer(job_title).data, status=status.HTTP_200_OK)
        except JobTitle.DoesNotExist:
            return Response({"error": "Job Title not found"}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            job_title = JobTitle.objects.get(pk=pk, is_active=True, organization=request.organization)
            if job_title.employees.exists():
                return Response({"error": "Cannot delete job title with employees, reassign employees first"},
                                status=status.HTTP_400_BAD_REQUEST)
            job_title.soft_delete(owner=request.user)
            return Response({"message": "Job Title deleted successfully"}, status=status.HTTP_200_OK)
        except JobTitle.DoesNotExist:
            return Response({"error": "Job Title not found"}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        department_id = request.query_params.get('department')
        level = request.query_params.get('level')

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (Q(name__icontains=query) | Q(job_title_id__icontains=query))
        if department_id:
            filter_q &= Q(department=department_id)
        if level:
            filter_q &= Q(level=level)

        job_titles = self.queryset.filter(filter_q).order_by("-date_created")

        paginator = Paginator(job_titles, page_size)
        page_obj = paginator.get_page(page)

        results = FullJobTitleSerializer(
            instance=page_obj.object_list,
            many=True
        ).data
        return Response(
            {
                'results': results,
                'pagination': {
                    'total': job_titles.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )
