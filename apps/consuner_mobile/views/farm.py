# views.py
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.consuner_mobile.serializers.farm import FarmDetailSerializer
from apps.consuner_mobile.swagger import add_swagger_to_mobile_farm_viewset
from apps.farm.models import Farm


@add_swagger_to_mobile_farm_viewset
class MobileFarmViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['GET'], url_path='my-farm')
    def get_my_farm(self, request):
        farmer = request.user.farmer
        farm = Farm.objects.filter(farmers=farmer).first()

        if not farm:
            return Response(
                {"detail": "No farm found for this user"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FarmDetailSerializer(farm)
        return Response(serializer.data, status=status.HTTP_200_OK)
