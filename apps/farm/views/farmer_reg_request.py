from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, viewsets
from django.utils import timezone

from apps.farm.models import FarmerRegistrationRequest
from apps.farm.serializers import farmer_reg_request
from apps.farm.serializers.farmer_reg_request import FarmerRegistrationRequestResponseSerializer, \
    FarmerRegistrationRequestSerializer
from apps.farm.utils import build_farmer_reg_filter_q
from apps.shared.literals import VIEW_FARMER_REG_REQUEST, APPROVE_OR_REJECT_FARMER_REG_REQUEST
from apps.shared.tasks import process_farmer_reg_req_export
from apps.shared.utils.permissions import UserPermission
from apps.sms.utils import send_sms


class FarmerRegistrationRequestViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        permissions = {
            'list': VIEW_FARMER_REG_REQUEST,
            'patch': APPROVE_OR_REJECT_FARMER_REG_REQUEST,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    @action(detail=True, methods=['PUT'], url_path='reject')
    def patch(self, request, pk):
        registration_request = get_object_or_404(
            FarmerRegistrationRequest,
            pk=pk
        )
        serializer = FarmerRegistrationRequestSerializer(data=request.data)
        if serializer.is_valid():
            if registration_request.status == "approved":
                return Response(
                    data={
                        "message": "Request has already been approved",
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if registration_request.status == "rejected":
                return Response(
                    data={
                        "message": "Request has already been rejected",
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            registration_request.status = "rejected"
            registration_request.reviewed_by = request.user
            registration_request.reviewed_at = timezone.now()
            registration_request.comments = serializer.validated_data['comments']
            registration_request.save(update_fields=['reviewed_by', 'reviewed_at', 'status', 'comments'])
            send_sms(registration_request.phone_number, f"""Hello {registration_request.first_name}!,
Your farmer registration request was not approved.
Reason: {registration_request.comments or "Please contact the farm office for further details."}
You may dial *923# to submit a new registration request.""")
        return Response(
            FarmerRegistrationRequestResponseSerializer(
                registration_request
            ).data
        )
    def retrieve(self, request ,pk=None):
        registration_request = get_object_or_404(
            FarmerRegistrationRequest,
            pk=pk
        )
        return Response(
            data=FarmerRegistrationRequestResponseSerializer(instance=registration_request).data,
            status=status.HTTP_200_OK
        )

    def list(self, request):
        try:
            page = request.query_params.get('page', 1)
            page_size = request.query_params.get('page_size', 10)
            export = request.query_params.get('export', 'false').lower()


            filter_q = build_farmer_reg_filter_q(request.query_params, request.organization)
            farmer_reg_requests = (
                FarmerRegistrationRequest.objects.select_related('reviewed_by', 'region', 'district')
                .filter(filter_q).order_by('-date_created').distinct()
            )

            export_response = None
            if export == 'true':
                if not farmer_reg_requests.exists():
                    export_response = 'No farmer registration request to export.'
                else:
                    filter_params = {
                        'user_id': request.user.id,
                        'organization_id': request.organization.id,
                        **request.query_params.dict(),
                    }
                    process_farmer_reg_req_export.delay(filter_params)
                    export_response = "Export started. You will receive a notification when the export is complete."

            paginator = Paginator(farmer_reg_requests, page_size)
            page_obj = paginator.get_page(page)

            results = FarmerRegistrationRequestResponseSerializer(instance=page_obj.object_list, many=True).data

            return Response({
                'export_response': export_response,
                'results': results,
                'pagination': {
                    'total': farmer_reg_requests.count(),
                    'page': page_obj.number,
                    'pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
