from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.hr.models import Employee, Training, TrainingAttendee
from apps.hr.serializers.training import FullTrainingSerializer, TrainingAttendeeSerializer, \
    TrainingSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import ADD_TRAINING_ATTENDEE, CREATE_TRAINING, DELETE_TRAINING, LIST_TRAININGS, \
    LIST_TRAINING_ATTENDEES, MARK_TRAINING_ATTENDEE_PRESENT, REMOVE_TRAINING_ATTENDEE, SET_ATTENDANCE_STATUS, \
    UPDATE_TRAINING, VIEW_TRAINING
from apps.shared.utils.permissions import UserPermission


class TrainingViewSet(viewsets.GenericViewSet):
    queryset = Training.objects.filter(is_active=True)
    serializer_class = TrainingSerializer

    def get_permissions(self):
        permissions = {
            'create': CREATE_TRAINING,
            'retrieve': VIEW_TRAINING,
            'update': UPDATE_TRAINING,
            'list': LIST_TRAININGS,
            'destroy': DELETE_TRAINING,
            'list_attendees': LIST_TRAINING_ATTENDEES,
            'mark_attendees_present': MARK_TRAINING_ATTENDEE_PRESENT,
            'add_attendee': ADD_TRAINING_ATTENDEE,
            'remove_attendee': REMOVE_TRAINING_ATTENDEE,
            'set_attendee_status': SET_ATTENDANCE_STATUS
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = TrainingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(FullTrainingSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
            serializer = self.get_serializer(training, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(FullTrainingSerializer(serializer.instance).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)

    def retrieve(self, request, pk=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
            return Response(FullTrainingSerializer(training).data, status=status.HTTP_200_OK)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        query = request.query_params.get('query')
        training_type = request.query_params.get('training_type')
        training_mode = request.query_params.get('training_mode')
        status_param = request.query_params.get('status', None)
        training_date_from = request.query_params.get('training_date_from')
        training_date_to = request.query_params.get('training_date_to')
        now = timezone.now()
        filter_q = Q(is_active=True, organization=request.organization)

        if query:
            filter_q &= (
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(training_id__icontains=query)
            )
        if training_type:
            filter_q &= Q(training_type=training_type)
        if training_mode:
            filter_q &= Q(training_mode=training_mode)

        if status_param in ['upcoming', 'ongoing']:
            filter_q &= (
                    Q(start_date__gt=now) |
                    Q(start_date__lte=now, end_date__gte=now)
            )
        elif status_param == 'completed':
            filter_q &= Q(end_date__lt=now)

        if training_date_from and training_date_to:
            filter_q &= Q(start_date__date__gte=training_date_from,  end_date__date__lte=training_date_to)
        elif training_date_from:
            filter_q &= Q(start_date__date__gte=training_date_from)
        elif training_date_to:
            filter_q &= Q(end_date__date__lte=training_date_to)

        trainings = Training.objects.filter(filter_q).order_by('-date_created')

        paginator = Paginator(trainings, page_size)
        page_obj = paginator.get_page(page)

        results = FullTrainingSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'results': results,
            'pagination': {
                'total': trainings.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)

            current_time = timezone.now()
            if training.start_date <= current_time:
                return Response({'error': 'Training has already started and cannot be deleted.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if training.end_date < current_time:
                return Response({'error': 'Training is already completed and cannot be deleted.'},
                                status=status.HTTP_400_BAD_REQUEST)
            training.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='attendees')
    def list_attendees(self, request, pk=None):
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        status_param = request.query_params.get('status')
        query = request.query_params.get('query')

        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)

        filter_q = Q(training=training, is_active=True)
        if status_param:
            filter_q &= Q(status=status_param)
        if query:
            filter_q &= (
                Q(employee__first_name__icontains=query) |
                Q(employee__last_name__icontains=query) |
                Q(employee__employee_id__icontains=query) |
                Q(employee__email__icontains=query) |
                Q(employee__phone_number__icontains=query[1:])
            )

        attendees = TrainingAttendee.objects.filter(filter_q) \
            .select_related('training', 'employee').order_by('-date_created')

        paginator = Paginator(attendees, page_size)
        page_obj = paginator.get_page(page)

        results = TrainingAttendeeSerializer(instance=page_obj.object_list, many=True).data

        return Response({
            'present': attendees.filter(status='present').count(),
            'absent': attendees.filter(status='absent').count(),
            'results': results,
            'pagination': {
                'total': attendees.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='add-attendee/(?P<employee_id>[^/.]+)')
    @transaction.atomic
    def add_attendee(self, request, pk=None, employee_id=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
            if training.end_date <= timezone.now():
                return Response({'error': 'Training is already completed.'}, status=status.HTTP_400_BAD_REQUEST)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            employee = Employee.objects.get(id=employee_id, organization=request.organization, is_active=True)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found or not active.'}, status=status.HTTP_404_NOT_FOUND)

        if TrainingAttendee.objects.filter(training=training, employee=employee).exists():
            return Response({'error': 'This employee is already registered for this training.'},
                            status=status.HTTP_400_BAD_REQUEST)

        TrainingAttendee.objects.create(
            training=training,
            employee=employee,
            created_by=request.user,
            status='absent'
        )
        return Response({'message': 'Employee successfully added to training.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'], url_path='remove-attendee/(?P<employee_id>[^/.]+)')
    @transaction.atomic
    def remove_attendee(self, request, pk=None, employee_id=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
            if training.end_date <= timezone.now():
                return Response({'error': 'Training is already completed.'}, status=status.HTTP_400_BAD_REQUEST)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            employee = Employee.objects.get(id=employee_id, organization=request.organization, is_active=True)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found or not active.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            training_attendee = TrainingAttendee.objects.get(training=training, employee=employee)
            training_attendee.delete()
            return Response({'message': 'Employee successfully removed from training.'}, status=status.HTTP_200_OK)
        except TrainingAttendee.DoesNotExist:
            return Response({'error': 'Employee is not registered for this training.'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['POST'], url_path='mark-attendees-present')
    @transaction.atomic
    def mark_attendees_present(self, request, pk=None):
        employee_ids = request.data.get('employees', [])
        mark_all = request.data.get('mark_all', False)
        actions = request.data.get('action', 'present').lower()

        if actions not in ['present', 'absent']:
            return Response({'error': 'Invalid action. Must be "present" or "absent".'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)

        if mark_all:
            attendees_qs = TrainingAttendee.objects.filter(training=training)
        else:
            if not isinstance(employee_ids, list) or not employee_ids:
                return Response({'error': 'Provide a non-empty employees list or set mark_all=true.'},
                                status=status.HTTP_400_BAD_REQUEST)
            attendees_qs = TrainingAttendee.objects.filter(training=training, employee_id__in=employee_ids)

        # Update status and timestamp
        attendees_qs.update(status=actions, marked_at=timezone.now())

        return Response({'message': f'Attendee marked as {actions}.', 'action': actions}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='set-attendance-status')
    @transaction.atomic
    def set_attendance_status(self, request, pk=None):
        """
        Toggles the attendance_status between 'ongoing' and 'completed'
        based on the 'status' field in the request body.
        """
        desired_status = request.data.get('status', 'completed').lower()

        if desired_status not in ['ongoing', 'completed']:
            return Response(
                {'error': 'Invalid status. Must be "ongoing" or "completed".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found.'}, status=status.HTTP_404_NOT_FOUND)

        training.attendance_status = desired_status
        training.save(update_fields=['attendance_status'])

        return Response(
            {'message': f'Attendance status set to {desired_status}.'},
            status=status.HTTP_200_OK
        )