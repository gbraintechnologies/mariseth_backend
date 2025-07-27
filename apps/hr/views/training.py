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
    LIST_TRAINING_ATTENDEES, MARK_TRAINING_ATTENDEE_PRESENT, REMOVE_TRAINING_ATTENDEE, UPDATE_TRAINING, VIEW_TRAINING
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
            'mark_attendee_present': MARK_TRAINING_ATTENDEE_PRESENT,
            'add_attendee': ADD_TRAINING_ATTENDEE,
            'remove_attendee': REMOVE_TRAINING_ATTENDEE
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

        if status_param == 'upcoming':
            filter_q &= Q(start_date__gt=timezone.now())
        elif status_param == 'completed':
            filter_q &= Q(end_date__lt=timezone.now())
        elif status_param == 'ongoing':
            filter_q &= Q(start_date__lte=timezone.now(), end_date__gte=timezone.now())

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

        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)
        filter_q = Q()
        if status_param:
            filter_q &= Q(status=status_param)

        attendees = TrainingAttendee.objects.filter(training=training, ).order_by('-date_created')

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

    @action(detail=True, methods=['POST'], url_path='mark-attendee-present/(?P<employee_id>[^/.]+)')
    @transaction.atomic
    def mark_attendee_present(self, request, pk=None, employee_id=None):
        try:
            training = Training.objects.get(pk=pk, is_active=True, organization=request.organization)
        except Training.DoesNotExist:
            return Response({'error': 'Training not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            employee = Employee.objects.get(id=employee_id, organization=request.organization, is_active=True)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found or not active.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            training_attendee = TrainingAttendee.objects.get(training=training, employee=employee)
            if training_attendee.status == 'present':
                return Response({'message': 'Employee already marked as present.'}, status=status.HTTP_200_OK)
            training_attendee.status = 'present'
            training_attendee.marked_at = timezone.now()
            training_attendee.save()
            return Response({'message': 'Employee marked as present.'}, status=status.HTTP_200_OK)
        except TrainingAttendee.DoesNotExist:
            return Response({'error': 'Employee is not registered for this training.'},
                            status=status.HTTP_404_NOT_FOUND)
