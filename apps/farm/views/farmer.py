from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import Credit
from apps.credit.serializers.credits import FullCreditSerializer
from apps.farm.models import Farm, Farmer, FarmerDocument
from apps.farm.serializers.farm import FarmSerializer, FullFarmSerializer
from apps.farm.serializers.farmer import FarmerSerializer, FullFarmerSerializer, ReassignSmallholderFarmerSerializer, FarmerDocumentSerializer
from apps.farm.swaagger import add_swagger_to_farmer_viewset
from apps.farm.utils import build_farmer_filter_q
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import CREATE_FARMER, DELETE_FARMER, GET_FARMER_CREDIT_HISTORY, GET_SMALLHOLDERS_BY_LEAD, \
    LIST_FARMERS, LIST_FARMS, UPDATE_FARMER, UPLOAD_FARMERS, VIEW_FARMER
from apps.shared.tasks.export_tasks import process_farmer_export
from apps.shared.utils.permissions import UserPermission
from apps.sms.utils import send_sms


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
            'upload_farmers': UPLOAD_FARMERS,
            'get_farmer_credit_history': GET_FARMER_CREDIT_HISTORY,
            'get_farmer_farms': LIST_FARMS,
            'remove_document': VIEW_FARMER,
            'add_document': VIEW_FARMER
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        try:
            serializer = FarmerSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                farmer = serializer.save(organization=request.organization)
                farmer_reg_request = farmer.farmer_reg_request
                if farmer_reg_request:
                    farmer_reg_request.status = "approved"
                    farmer_reg_request.reviewed_by = request.user
                    farmer_reg_request.reviewed_at = timezone.now()
                    farmer_reg_request.save(update_fields=['status'])
                    send_sms.delay(farmer_reg_request.phone_number, f"""Hello {farmer_reg_request.first_name}!,
    Your farmer registration has been approved. To view your details, dial *923# and select Option 4: My Account.""")
                return Response(FullFarmerSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            print(ex)
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
        export = request.query_params.get('export', 'false').lower()

        if export == 'true' and not request.query_params.get('farmer_type'):
            return Response({'error': 'Please select a farmer type.'}, status=status.HTTP_400_BAD_REQUEST)

        filter_q = build_farmer_filter_q(request.query_params, request.organization)

        farmers = (
            Farmer.objects.select_related('farm', 'lead_farmer', 'created_by', 'region', 'district')
            .filter(filter_q).order_by('-date_created').distinct()
        )

        export_response = None
        if export == 'true':
            if not farmers.exists():
                export_response = 'No farmers to export.'
            else:
                filter_params = {
                    'user_id': request.user.id,
                    'organization_id': request.organization.id,
                    **request.query_params.dict(),
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
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
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

    @action(detail=True, methods=['GET'], url_path='credit-history')
    def get_farmer_credit_history(self, request, pk):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)
        credit_history = Credit.objects.filter(farmer=farmer, is_active=True).order_by('-date_created')
        paginator = Paginator(credit_history, page_size)
        page_obj = paginator.get_page(page)
        results = FullCreditSerializer(instance=page_obj.object_list, many=True).data
        return Response({
            'results': results,
            'pagination': {
                'total': credit_history.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], url_path='farms')
    def get_farmer_farms(self, request, pk=None):
        """
        Get paginated list of farms owned by the lead farmer
        """
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

        filter_q = Q(farmer=farmer, is_active=True)

        if query:
            filter_q &= (
                    Q(name__icontains=query) |
                    Q(farm_id__icontains=query) |
                    Q(location__icontains=query)
            )

        farms = Farm.objects.filter(filter_q).order_by('-date_created')
        paginator = Paginator(farms, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullFarmSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': farms.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })

    @action(detail=False, methods=['POST'], url_path='reassign-smallholder-farmer')
    def reassign_smallholder_farmer(self, request):
        serializer = ReassignSmallholderFarmerSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='add-document')
    @transaction.atomic
    def add_document(self, request, pk=None):
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FarmerDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(farmer=farmer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['DELETE'], url_path='remove-document/(?P<document_id>[^/.]+)')
    @transaction.atomic
    def remove_document(self, request, pk=None, document_id=None):
        try:
            farmer = Farmer.objects.get(pk=pk, is_active=True, organization=request.organization)
            document = farmer.documents.get(pk=document_id)
            document.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except Farmer.DoesNotExist:
            return Response({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)
        except FarmerDocument.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
