from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.shared.literals import CREATE_HELP, DELETE_HELP, UPDATE_HELP
from apps.shared.models import Help
from apps.shared.serializers.help import HelpSerializer, FullHelpSerializer
from apps.shared.swagger import add_swagger_to_help_viewset
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_help_viewset
class HelpViewSet(viewsets.GenericViewSet):
    serializer_class = HelpSerializer
    queryset = Help.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_HELP,
            'update': UPDATE_HELP,
            'destroy': DELETE_HELP,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = HelpSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(organization=request.organization)
            return Response(FullHelpSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            help_instance = Help.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = HelpSerializer(instance=help_instance, data=request.data, partial=True,
                                        context={'request': request})
            if serializer.is_valid():
                serializer.save(organization=request.organization)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Help.DoesNotExist:
            return Response({'error': 'Help not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            help_instance = Help.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullHelpSerializer(help_instance).data, status=status.HTTP_200_OK)
        except Help.DoesNotExist:
            return Response({'error': 'Help not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (Q(title__icontains=query) | Q(description__icontains=query))

        help_instances = Help.objects.filter(filter_q).order_by('-date_created')

        paginator = Paginator(help_instances, page_size)
        page_obj = paginator.get_page(page)

        results = FullHelpSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'results': results,
            'pagination': {
                'total': help_instances.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            help_instance = Help.objects.get(pk=pk, is_active=True, organization=request.organization)
            help_instance.soft_delete(owner=request.user)
            return Response({'message': 'Help deleted successfully'}, status=status.HTTP_200_OK)
        except Help.DoesNotExist:
            return Response({'error': 'Help not found'}, status=status.HTTP_404_NOT_FOUND)