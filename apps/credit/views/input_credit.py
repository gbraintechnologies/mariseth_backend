from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.credit.models import InputCredit, InputCreditPurchase
from apps.credit.serializers.input_credit import CreateInputCreditSerializer, FullInputCreditSerializer, \
    InputCreditPurchaseListSerializer, InputCreditPurchaseSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import (
    CREATE_INPUT_CREDIT, CREATE_INPUT_CREDIT_PURCHASE, DELETE_INPUT_CREDIT, DELETE_INPUT_CREDIT_PURCHASE,
    LIST_INPUT_CREDIT, LIST_INPUT_CREDIT_PURCHASE, UPDATE_INPUT_CREDIT, VIEW_INPUT_CREDIT
)
from apps.shared.utils.permissions import UserPermission


class InputCreditViewSet(viewsets.GenericViewSet):
    serializer_class = FullInputCreditSerializer
    queryset = InputCredit.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_INPUT_CREDIT,
            'update': UPDATE_INPUT_CREDIT,
            'destroy': DELETE_INPUT_CREDIT,
            'list': LIST_INPUT_CREDIT,
            'retrieve': VIEW_INPUT_CREDIT,
            'input_credit_purchase': CREATE_INPUT_CREDIT_PURCHASE,
            'list_input_credit_purchases': LIST_INPUT_CREDIT_PURCHASE,
            'delete_input_credit_purchase': DELETE_INPUT_CREDIT_PURCHASE,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def create(self, request):
        serializer = CreateInputCreditSerializer(data=request.data)
        if serializer.is_valid():
            input_credit = serializer.save(
                organization=request.organization,
                created_by=request.user
            )
            input_credit.input_credit_id = f"IC-{input_credit.id:02d}"
            input_credit.save()
            return Response(FullInputCreditSerializer(input_credit).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            input_credit = InputCredit.objects.get(pk=pk, organization=request.organization)
        except InputCredit.DoesNotExist:
            return Response({'error': 'InputCredit not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FullInputCreditSerializer(input_credit).data)

    def update(self, request, pk=None):
        try:
            input_credit = InputCredit.objects.get(pk=pk, organization=request.organization)
        except InputCredit.DoesNotExist:
            return Response({'error': 'InputCredit not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreateInputCreditSerializer(input_credit, data=request.data, partial=True)
        if serializer.is_valid():
            input_credit = serializer.save()
            return Response(FullInputCreditSerializer(input_credit).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            input_credit = InputCredit.objects.get(pk=pk, is_active=True, organization=request.organization)
        except InputCredit.DoesNotExist:
            return Response({'error': 'InputCredit not found'}, status=status.HTTP_404_NOT_FOUND)

        if input_credit.quantity > 0:
            return Response(
                {'error': 'This input credit cannot be deleted because it still has stock available.'}
                , status=status.HTTP_400_BAD_REQUEST)
        input_credit.soft_delete(request.user)
        return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='purchase')
    def input_credit_purchase(self, request):
        serializer = InputCreditPurchaseSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            purchase = serializer.save()
            return Response(InputCreditPurchaseListSerializer(purchase).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['DELETE'], url_path='delete-purchase/(?P<purchase_id>[^/.]+)')
    def delete_input_credit_purchase(self, request, purchase_id=None):
        """
        Deletes an input credit purchase and reverses the associated stock movements.
        """
        try:
            purchase = InputCreditPurchase.objects.get(pk=purchase_id, is_active=True, organization=request.organization)
            purchase.soft_delete(request.user)
            with transaction.atomic():
                purchase.reverse_input_purchase()
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except InputCreditPurchase.DoesNotExist:
            return Response({'error': 'InputCreditPurchase not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['GET'], url_path='input-credit-purchases')
    def list_input_credit_purchases(self, request, *args, **kwargs):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        filter_q = Q(is_active=True)
        input_credit_id = request.query_params.get('input_credit')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if input_credit_id:
            filter_q &= Q(input_credit_id=input_credit_id)

        if start_date:
            filter_q &= Q(purchase_date__gte=start_date)

        if end_date:
            filter_q &= Q(purchase_date__lte=end_date)

        queryset = InputCreditPurchase.objects.filter(filter_q)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': InputCreditPurchaseListSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def list(self, request):
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
