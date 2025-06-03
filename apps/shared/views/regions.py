from rest_framework import viewsets

from apps.shared.models import Region
from apps.shared.serializers.regions import RegionSerializer
from apps.shared.swagger import add_swagger_to_region_viewset


@add_swagger_to_region_viewset
class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegionSerializer
    queryset = Region.objects.all().prefetch_related('districts')
    lookup_field = 'code'
