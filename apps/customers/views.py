from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer, FullCustomerSerializer
from apps.customers.swagger import add_swagger_to_customer_viewset
from apps.shared.literals import (CREATE_CUSTOMER, DELETE_CUSTOMER, LIST_CUSTOMERS, UPDATE_CUSTOMER, VIEW_CUSTOMER)
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_customer_viewset
class CustomerViewSet(viewsets.GenericViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.filter(is_active=True)

    def get_permissions(self):
        permissions = {
            'create': CREATE_CUSTOMER,
            'update': UPDATE_CUSTOMER,
            'destroy': DELETE_CUSTOMER,
            'list': LIST_CUSTOMERS,
            'retrieve': VIEW_CUSTOMER
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request):
        serializer = CustomerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            customer = serializer.save()
            return Response(FullCustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            customer = Customer.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = CustomerSerializer(instance=customer, data=request.data, partial=True,
                                            context={'request': request})
            if serializer.is_valid():
                customer = serializer.save()
                return Response(FullCustomerSerializer(customer).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        try:
            customer = Customer.objects.get(pk=pk, is_active=True, organization=request.organization)
            customer.is_active = False
            customer.save()
            return Response({'message': 'Customer deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            customer = Customer.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullCustomerSerializer(customer).data, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')

        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (
                    Q(name__icontains=query) |
                    Q(phone_number__icontains=query) |
                    Q(email__icontains=query) |
                    Q(customer_id__icontains=query)
            )

        customers = Customer.objects.filter(filter_q).order_by('name')
        paginator = Paginator(customers, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'results': FullCustomerSerializer(page_obj.object_list, many=True).data,
            'pagination': {
                'total': customers.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
