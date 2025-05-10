from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.models import Organization
from apps.organizations.serializers.organization import FullOrganizationSerializer, OrganizationSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.utils.permissions import UserPermission


class OrganizationViewSet(viewsets.GenericViewSet):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            # 'create': CREATE_ORGANIZATION,
            # 'update': UPDATE_ORGANIZATION,
            # 'destroy': DELETE_ORGANIZATION,
            # 'list': LIST_ORGANIZATIONS,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def create(self, request):
        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            organization = serializer.save()
            return Response(OrganizationSerializer(organization).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk, is_active=True)
            serializer = OrganizationSerializer(
                instance=organization, data=request.data, partial=True)
            if serializer.is_valid():
                organization = serializer.save()
                return Response(FullOrganizationSerializer(organization).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk, is_active=True)
            organization.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_204_NO_CONTENT)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk, is_active=True)
            return Response(FullOrganizationSerializer(organization).data, status=status.HTTP_201_CREATED)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        events = Organization.objects.filter(is_active=True).order_by('name')
        paginator = Paginator(events, page_size)
        page_obj = paginator.get_page(page)

        results = FullOrganizationSerializer(
            instance=page_obj.object_list,
            many=True
        ).data

        return Response(
            {
                'results': results,
                'pagination': {
                    'total': events.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )
