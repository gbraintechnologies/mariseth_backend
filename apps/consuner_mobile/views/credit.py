from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.consuner_mobile.serializers.credit import MobileActiveCreditSerializer, MobileCreditApplicationSerializer, \
    MobileCreditPaybackSerializer, MobileCreditSerializer
from apps.credit.serializers.input_credit import FullInputCreditSerializer
from apps.consuner_mobile.swagger import add_swagger_to_mobile_credit_viewset
from apps.credit.models import Credit, CreditPayback, InputCredit


@add_swagger_to_mobile_credit_viewset
class MobileCreditViewSet(viewsets.GenericViewSet):
    serializer_class = MobileCreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get credits for the logged-in farmer"""
        farmer = self.request.user.farmer
        return Credit.objects.filter(farmer=farmer, approval_status='approved').order_by('-date_created')

    @action(detail=False, methods=['GET'], url_path='active-credit')
    def get_active_credit(self, request):
        """
        Get the active credit for the logged-in farmer
        """
        farmer = request.user.farmer
        active_credit = Credit.objects.filter(
            farmer=farmer,
            approval_status='approved',
            payment_status__in=['active', 'partial', 'overdue']
        ).order_by('-date_created').first()

        if not active_credit:
            return Response(
                {"message": "No active credit found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MobileActiveCreditSerializer(active_credit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='credit-history')
    def get_credit_history(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        status_filter = request.query_params.get('status')
        type_filter = request.query_params.get('type')
        farmer = request.user.farmer
        queryset = Credit.objects.filter(
            farmer=farmer,
        ).order_by('-date_created')
        if status_filter:
            queryset = queryset.filter(payment_status=status_filter)
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': MobileCreditSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='payback-history')
    def get_payback_history(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        farmer = request.user.farmer
        paybacks = CreditPayback.objects.filter(
            credit__farmer=farmer,
        ).order_by('-date_created')

        credit_id = request.query_params.get('credit_id')
        if credit_id:
            paybacks = paybacks.filter(credit__credit_id=credit_id)
        method_filter = request.query_params.get('method')
        if method_filter:
            paybacks = paybacks.filter(payback_method=method_filter)
        paginator = Paginator(paybacks, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': MobileCreditPaybackSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': paybacks.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='apply-for-credit')
    def apply_for_credit(self, request):
        serializer = MobileCreditApplicationSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            credit_app = serializer.save()
            return Response(MobileCreditSerializer(credit_app).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='list-input-credits')
    def list_input_credits(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        category_id = request.query_params.get('category')

        queryset = InputCredit.objects.filter(is_active=True, organization=request.organization)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullInputCreditSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
