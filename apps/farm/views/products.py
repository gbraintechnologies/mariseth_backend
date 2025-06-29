from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farm, Product
from apps.farm.serializers.farm import FarmSerializer
from apps.farm.serializers.products import FullProductSerializer, ProductSerializer
from apps.farm.swaagger import add_swagger_to_product_viewset
from apps.shared.literals import (
    CREATE_PRODUCT, DELETE_PRODUCT, LIST_PRODUCTS, UPDATE_PRODUCT,
    UPLOAD_PRODUCTS, VIEW_PRODUCT
)
from apps.shared.tasks.export_tasks import process_product_export
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_product_viewset
class ProductViewSet(viewsets.GenericViewSet):
    serializer_class = FarmSerializer
    queryset = Farm.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_PRODUCT,
            'update': UPDATE_PRODUCT,
            'retrieve': VIEW_PRODUCT,
            'list': LIST_PRODUCTS,
            'destroy': DELETE_PRODUCT,
            'upload_products': UPLOAD_PRODUCTS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = ProductSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                FullProductSerializer(product).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = ProductSerializer(instance=product, data=request.data, partial=True,
                                           context={'request': request})
            if serializer.is_valid():
                product = serializer.save()
                return Response(
                    FullProductSerializer(product).data,
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def retrieve(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullProductSerializer(product).data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        product_type = request.query_params.get('type')
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        season_status = request.query_params.get('season_status')
        export = request.query_params.get('export', 'false').lower()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        last_updated_from = request.query_params.get('last_updated_from')
        last_updated_to = request.query_params.get('last_updated_to')

        filter_q = Q(is_active=True, organization=request.organization)

        if export == 'true' and not product_type:
            return Response({'error': 'Please select a product type.'}, status=status.HTTP_400_BAD_REQUEST)

        if product_type:
            filter_q &= Q(type=product_type)
        if category:
            filter_q &= Q(category_id=category)
        if status_filter:
            filter_q &= Q(status=status_filter)
        if season_status:
            filter_q &= Q(season_status=season_status)
        if date_from and date_to:
            filter_q &= Q(date_created__date__range=[date_from, date_to])
        if last_updated_from and last_updated_to:
            filter_q &= Q(last_updated__date__range=[last_updated_from, last_updated_to])
        if query:
            filter_q &= (
                    Q(name__icontains=query) |
                    Q(product_type__icontains=query)
            )

        products = Product.objects.select_related(
            'category', 'weight_metric', 'quantity_metric', 'created_by'
        ).filter(filter_q).order_by("-last_updated")

        # Handle export
        export_response = None
        if export == 'true':
            ilter_params = {
                'query': query,
                'type': product_type,
                'category': category,
                'status': status_filter,
                'season_status': season_status,
                'date_range': f"{date_from} to {date_to}",
                'user_id': request.user.id,
                'organization_id': request.organization.id,
            }
            process_product_export.delay(ilter_params)
            export_response = 'Export started. You will receive an email when ready.'

        paginator = Paginator(products, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'export_response': export_response,
            'results': FullProductSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': products.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_active=True, organization=request.organization)
            product.soft_delete(owner=request.user)
            return Response(
                {'message': 'Product deleted successfully'},
                status=status.HTTP_200_OK
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['POST'], url_path='upload-product')
    @transaction.atomic
    def upload_products(self, request):
        pass
