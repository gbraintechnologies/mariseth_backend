from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.serializers.invoices import InvoiceSerializer
from apps.accounting.serializers.waybills import InflowOrderListRetrieveSerializer
from apps.outflow.models import OutflowOrder, OutflowOrderPayments
from apps.outflow.serializers.outflow import FullOutflowOrderSerializer
from apps.shared.literals import LIST_INVOICES, VIEW_INVOICE
from apps.shared.utils.permissions import UserPermission


class InvoiceViewSet(viewsets.ViewSet):
    queryset = OutflowOrder.objects.all()
    serializer_class = InflowOrderListRetrieveSerializer

    def get_permissions(self):
        permissions = {
            'list': LIST_INVOICES,
            'retrieve': VIEW_INVOICE
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)

        invoices = OutflowOrderPayments.objects.filter(invoice_id__isnull=False, is_active=True).order_by(
            "-date_created")

        paginator = Paginator(invoices, page_size)
        page_obj = paginator.get_page(page)

        serializer = InvoiceSerializer(page_obj.object_list, many=True)

        return Response({
            'results': serializer.data,
            'pagination': {
                'total': invoices.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        try:
            invoice = OutflowOrderPayments.objects.get(pk=pk, is_active=True)
            outflow = OutflowOrder.objects.get(pk=invoice.outflow_order.id, is_active=True)
            return Response(
                data={
                    "invoice": InvoiceSerializer(invoice).data,
                    "outflow": FullOutflowOrderSerializer(outflow).data,
                },
                status=status.HTTP_200_OK
            )
        except OutflowOrderPayments.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        except OutflowOrder.DoesNotExist:
            return Response({'error': 'Outflow Order not found'}, status=status.HTTP_404_NOT_FOUND)
