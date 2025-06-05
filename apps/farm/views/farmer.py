from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.farm.models import Farm, Farmer
from apps.farm.serializers.farm import FarmSerializer
from apps.farm.serializers.farmer import FarmerSerializer, FullFarmerSerializer
from apps.farm.swaagger import add_swagger_to_farmer_viewset
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import CREATE_FARMER, DELETE_FARMER, GET_SMALLHOLDERS_BY_LEAD, LIST_FARMERS, UPDATE_FARMER, \
    UPLOAD_FARMERS, VIEW_FARMER
from apps.shared.tasks.export_tasks import process_farmer_export
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_farmer_viewset
class FarmerViewSet(viewsets.GenericViewSet):
    serializer_class = FarmSerializer
    queryset = Farm.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_FARMER,
            'update': UPDATE_FARMER,
            'retrieve': VIEW_FARMER,
            'list': LIST_FARMERS,
            'destroy': DELETE_FARMER,
            'get_smallholders_by_lead': GET_SMALLHOLDERS_BY_LEAD,
            'upload_farmers': UPLOAD_FARMERS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = FarmerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(organization=request.organization)
            return Response(FullFarmerSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = FarmerSerializer(instance=farmer, data=request.data, partial=True,
                                          context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullFarmerSerializer(farmer).data, status=status.HTTP_200_OK)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        farmer_type = request.query_params.get('farmer_type')
        ownership_type = request.query_params.get('ownership_type')
        country = request.query_params.get('country')
        export = request.query_params.get('export', 'false').lower()
        # Lead: This is used when the you want to fetch the smallholder farmers for a lead farmer
        lead = request.query_params.get('lead')

        if export == 'true' and not farmer_type:
            return Response({'error': 'Please select a farmer type.'}, status=status.HTTP_400_BAD_REQUEST)

        filter_q = Q(is_active=True, organization=request.organization)

        if farmer_type:
            filter_q &= Q(type=farmer_type)

        if ownership_type:
            filter_q &= Q(farm__land_ownership=ownership_type)

        if country:
            filter_q &= Q(country__iexact=country)

        if lead:
            filter_q &= Q(lead_farmer__id=lead)

        if query:
            filter_q &= (
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(phone_number__icontains=query) |
                    Q(email__icontains=query) |
                    Q(farm__name__icontains=query) |
                    Q(farmer_id__icontains=query)
            )

        farmers = Farmer.objects.select_related('farm', 'lead_farmer').filter(filter_q).order_by(
            '-date_created').distinct()

        export_response = None
        if export == 'true':
            filter_params = {
                'user_id': request.user.id,
                'organization_id': request.organization.id,
                'query': request.query_params.get('query'),
                'type': request.query_params.get('type'),
                'country': request.query_params.get('country'),
                'date_from': request.query_params.get('date_from'),
                'date_to': request.query_params.get('date_to')
            }
            process_farmer_export.delay(filter_params)
            export_response = "Export started. You will receive a notification when the export is complete."

        paginator = Paginator(farmers, page_size)
        page_obj = paginator.get_page(page)

        results = FullFarmerSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'export_response': export_response,
            'results': results,
            'pagination': {
                'total': farmers.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
            farmer.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_204_NO_CONTENT)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST'], url_path='upload-farmer')
    @transaction.atomic
    def upload_farmers(self, request):
        pass

    @action(detail=True, methods=['GET'], url_path='smallholders-by-lead')
    def get_smallholders_by_lead(self, request, pk):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')

        filter_q = Q(is_active=True, organization=request.organization,
                     type='smallholder', lead_farmer__id=pk)
        if query:
            filter_q &= (
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(phone_number__icontains=query) |
                    Q(email__icontains=query) |
                    Q(farm__name__icontains=query) |
                    Q(farmer_id__icontains=query)
            )
        farmers = Farmer.objects.select_related(
            'farm',
            'lead_farmer',
            'region',
            'district'
        ).filter(filter_q).order_by('-date_created').distinct()
        paginator = Paginator(farmers, page_size)
        page_obj = paginator.get_page(page)
        results = FullFarmerSerializer(instance=page_obj.object_list, many=True).data
        return Response({
            'results': results,
            'pagination': {
                'total': farmers.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
