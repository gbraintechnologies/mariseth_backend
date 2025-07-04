from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.consuner_mobile.serializers.lead_farmer import FarmSerializer, \
    MobileAddSmallholderFarmerSerializer
from apps.consuner_mobile.swagger import add_swagger_to_mobile_lead_farmer_viewset
from apps.farm.models import Farm, Farmer
from apps.farm.serializers.farm import FullFarmSerializer
from apps.farm.serializers.farmer import FullFarmerSerializer
from apps.shared.utils.decorators import lead_farmer_required
from apps.farm.views.farm import FarmViewSet


@add_swagger_to_mobile_lead_farmer_viewset
class MobileLeadFarmerViewSet(viewsets.GenericViewSet):
    queryset = Farmer.objects.none()
    serializer_class = FullFarmerSerializer
    permission_classes = [IsAuthenticated]

    def get_lead_farmer(self):
        """Helper method to get and validate lead farmer"""
        if not self.request.user.farmer.type == 'lead':
            raise PermissionDenied("Only lead farmers can access this endpoint")
        return self.request.user.farmer

    @action(detail=False, methods=['GET'], url_path='farms')
    @lead_farmer_required
    def get_farms(self, request):
        """
        Get paginated list of farms owned by the lead farmer
        """
        try:
            lead_farmer = self.get_lead_farmer()
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')

        filter_q = Q(farmer=lead_farmer, is_active=True)

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
            'results': FarmSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': farms.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })

    @action(detail=False, methods=['GET'], url_path='smallholders')
    @lead_farmer_required
    def get_smallholders(self, request):

        try:
            lead_farmer = self.get_lead_farmer()
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')

        filter_q = Q(lead_farmer=lead_farmer, is_active=True, type='smallholder')

        if query:
            filter_q &= (
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(farmer_id__icontains=query) |
                    Q(phone_number__icontains=query) |
                    Q(farm__name__icontains=query)
            )

        smallholders = Farmer.objects.filter(filter_q).select_related(
            'farm', 'user', 'district'
        ).order_by('-date_created')

        paginator = Paginator(smallholders, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullFarmerSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': smallholders.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })

    @action(detail=False, methods=['POST'], url_path='add-new-farmer')
    @lead_farmer_required
    def add_new_farmer(self, request):
        serializer = MobileAddSmallholderFarmerSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(organization=request.organization)
            return Response(FullFarmerSerializer(serializer.instance).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='add-new-farm')
    @lead_farmer_required
    def add_new_farm(self, request):
        request.data['farmer'] = request.user.farmer.id
        create_farm = FarmViewSet.create(self, request)
        return create_farm

    @action(detail=False, methods=['POST'], url_path='edit-farm/(?P<farm_id>[^/.]+)')
    @lead_farmer_required
    def edit_farm(self, request, farm_id):
        request.data['farmer'] = request.user.farmer.id
        update_farm = FarmViewSet.update(self, request, farm_id)
        return update_farm

