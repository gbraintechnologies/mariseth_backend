# views.py
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.consuner_mobile.serializers.lead_farmer import FarmSerializer
from apps.consuner_mobile.swagger import add_swagger_to_mobile_lead_farmer_viewset
from apps.farm.models import Farm, Farmer
from apps.farm.serializers.farmer import FarmerSerializer


@add_swagger_to_mobile_lead_farmer_viewset
class MobileLeadFarmerViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_lead_farmer(self):
        """Helper method to get and validate lead farmer"""
        if not self.request.user.farmer.type == 'lead':
            raise PermissionDenied("Only lead farmers can access this endpoint")
        return self.request.user.farmer

    @action(detail=False, methods=['GET'], url_path='farms')
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
            'results': FarmerSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': smallholders.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
