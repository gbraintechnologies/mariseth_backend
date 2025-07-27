from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import CREATE_CUSTOM_TYPE, DELETE_CUSTOM_TYPE, UPDATE_CUSTOM_TYPE
from apps.shared.models import CustomType
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.shared.swagger import add_swagger_to_custom_type_viewset
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_custom_type_viewset
class CustomTypeViewSet(viewsets.GenericViewSet):
    queryset = CustomType.objects.all()
    serializer_class = CustomTypeSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_CUSTOM_TYPE,
            'update': UPDATE_CUSTOM_TYPE,
            'destroy': DELETE_CUSTOM_TYPE,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def create(self, request):
        serializer = CustomTypeSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            custom_type = serializer.save()
            return Response(CustomTypeSerializer(custom_type).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            custom_type = CustomType.objects.get(pk=pk, is_active=True, organization=request.organization)
            if custom_type.is_default:
                return Response({'error': 'You cannot update this custom type.'},
                                status=status.HTTP_403_FORBIDDEN)
            serializer = CustomTypeSerializer(
                instance=custom_type, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                custom_type = serializer.save()
                return Response(CustomTypeSerializer(custom_type).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CustomType.DoesNotExist:
            return Response({'error': 'CustomType not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        try:
            custom_type = CustomType.objects.get(pk=pk, is_active=True, organization=request.organization)
            custom_type.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except CustomType.DoesNotExist:
            return Response({'error': 'CustomType not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query', None)
        organization = request.organization
        custom_types = CustomType.objects.filter(
            is_active=True, organization=organization
        )
        if query:
            custom_types = custom_types.filter(category_name__icontains=query)
        custom_types = custom_types
        default_custom_types = CustomType.objects.filter(is_active=True, is_default=True).exclude(
            is_hidden=True
        )
        combined_custom_types = custom_types.union(default_custom_types).order_by('-id')
        paginator = Paginator(combined_custom_types, page_size)
        page_obj = paginator.get_page(page)

        results = CustomTypeSerializer(
            instance=page_obj.object_list,
            many=True
        ).data

        return Response(
            {
                'results': results,
                'pagination': {
                    'total': custom_types.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )
