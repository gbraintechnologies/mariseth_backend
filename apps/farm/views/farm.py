from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farm
from apps.farm.serializers.farm import FarmDeleteSerializer, FarmProductDeleteSerializer, FarmSerializer, \
    FullFarmSerializer
from apps.farm.swaagger import add_swagger_to_farm_viewset
from apps.shared.literals import CREATE_FARM, DELETE_FARM, DELETE_FARM_PRODUCTS, LIST_FARMS, UPDATE_FARM, UPLOAD_FARMS, \
    VIEW_FARM
from apps.shared.tasks.export_tasks import process_farm_export
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_farm_viewset
class FarmViewSet(viewsets.GenericViewSet):
    serializer_class = FarmSerializer
    queryset = Farm.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_FARM,
            'update': UPDATE_FARM,
            'retrieve': VIEW_FARM,
            'list': LIST_FARMS,
            'destroy': DELETE_FARM,
            'delete_farm_products': DELETE_FARM_PRODUCTS,
            'upload_farms': UPLOAD_FARMS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = FarmSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            farm = serializer.save()
            return Response(FullFarmSerializer(farm).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            farm = Farm.objects.get(pk=pk, is_active=True)
            if farm.organization != request.organization:
                return Response({'error': 'You cannot update this farm.'}, status=status.HTTP_403_FORBIDDEN)
            serializer = FarmSerializer(instance=farm, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                farm = serializer.save()
                return Response(FullFarmSerializer(farm).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Farm.DoesNotExist:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            farm = Farm.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullFarmSerializer(farm).data, status=status.HTTP_200_OK)
        except Farm.DoesNotExist:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        farm_type = request.query_params.get('farm_type')
        farm_size = request.query_params.get('farm_size')
        crop_type = request.query_params.get('crop_type')
        export = request.query_params.get('export', 'false').lower()
        # TODO: ADD A CROP FILTER

        if export == 'true' and not farm_type:
            return Response({'error': 'Please select a farm type.'}, status=status.HTTP_400_BAD_REQUEST)

        filter_q = Q(is_active=True, organization=request.organization)

        if farm_type:
            filter_q &= Q(farm_type=farm_type)

        if farm_size:
            filter_q &= Q(farm_size=farm_size)

        if crop_type:
            filter_q &= Q(crop_type=crop_type)

        if query:
            filter_q &= (
                    Q(name__icontains=query) |
                    Q(farm_id__icontains=query)
            )

        farms = (
            Farm.objects
            .select_related('created_by')
            .prefetch_related('farmproduct_set')
            .filter(filter_q)
            .order_by("-date_created")
            .distinct()
        )

        export_response = None
        if export == 'true':
            filter_params = {
                'user_id': request.user.id,
                'organization_id': request.organization.id,
                'query': request.query_params.get('query'),
                'farm_type': request.query_params.get('farm_type'),
                'district': request.query_params.get('district'),
                'date_from': request.query_params.get('date_from'),
                'date_to': request.query_params.get('date_to')
            }
            process_farm_export.delay(filter_params)
            export_response = 'Export started. You will receive a notification when it is done.'

        paginator = Paginator(farms, page_size)
        page_obj = paginator.get_page(page)

        results = FullFarmSerializer(
            instance=page_obj.object_list,
            many=True
        ).data
        return Response(
            {
                'export_response': export_response,
                'results': results,
                'pagination': {
                    'total': farms.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request, pk=None):
        farm = Farm.objects.filter(pk=pk, is_active=True, organization=request.organization).first()
        if not farm:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FarmDeleteSerializer(farm, data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        farm.soft_delete(owner=request.user)
        return Response({'message': 'Farm deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], url_path='delete-farm-products')
    @transaction.atomic
    def delete_farm_products(self, request, pk=None):
        try:
            farm = Farm.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Farm.DoesNotExist:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FarmProductDeleteSerializer(
            data=request.data,
            context={'farm': farm, 'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        farm_products = serializer.validated_data['farm_product_ids']
        farm_products.update(is_active=False, deleted_by=request.user, date_deleted=timezone.now())
        return Response(
            {'message': f'Farm products deleted successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['POST'], url_path='upload-farms')
    def upload_farms(self, request):
        # TODO: KNOW WHAT WILL BE UPLOADED OR A COPY OF AN UPLOAD CV
        return Response({'message': 'The code to add farms is not written'}, status=status.HTTP_200_OK)
