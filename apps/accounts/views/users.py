from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from rest_framework import status, views, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import AppGroup, AppPermission
from apps.accounts.serializers.users import GroupSerializer, GroupWithRankSerializer, NewUserSerializer, \
    PermissionSerializer, UserSerializer
from apps.accounts.swagger import add_swagger_to_groups_view, add_swagger_to_permission_list_view, \
    add_swagger_to_user_account_viewset
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE
from apps.shared.literals import ADD_ADMIN, CREATE_GROUPS_AND_ROLES, DELETE_ADMIN, DELETE_GROUPS_AND_ROLES, \
    LIST_ADMINS, UPDATE_ADMIN, UPDATE_GROUPS_AND_ROLES, VIEW_GROUPS_AND_ROLES
from apps.shared.utils.permissions import UserPermission

User = get_user_model()
from apps.organizations.models import OrganizationUser


@add_swagger_to_user_account_viewset
class UserAccountViewSet(viewsets.GenericViewSet):
    serializer_class = NewUserSerializer
    queryset = User.objects.all()

    def get_permissions(self):
        permissions = {
            'create': ADD_ADMIN,
            'update': UPDATE_ADMIN,
            'destroy': DELETE_ADMIN,
            'list': LIST_ADMINS,
            'retrieve': LIST_ADMINS
        }
        user_permission = permissions[self.action]
        print(f'user: {self.request.user}'
              f' permission to check:{user_permission}')
        return [
            IsAuthenticated(), UserPermission(user_permission)
        ]

    def create(self, request):
        """
        Register a new user.
        """
        serializer = NewUserSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Update an existing user.
        """
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        Delete a user.
        """
        try:
            user = self.get_queryset().get(is_active=True, id=pk)
            fields_to_encrypt = ['email', 'phone_number', 'username']
            user.soft_delete(owner=request.user,
                             fields_to_encrypt=fields_to_encrypt)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        """
        List all users.
        """
        organization = request.organization
        if not organization:
            return Response({'detail': 'User does not belong to any organization.'}, status=status.HTTP_400_BAD_REQUEST)

        query = request.query_params.get('query')
        user_type = request.query_params.get('user_type', 'admin')
        queryset = User.objects.filter(
            is_active=True,
            organization_users__organization=organization
        ).prefetch_related(
            'groups',
            Prefetch(
                'organization_users',
                queryset=OrganizationUser.objects.select_related('organization')
            )
        )
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone_number__icontains=query) |
                Q(email__iexact=query)
            )
        if user_type:
            queryset = queryset.filter(user_type=user_type)

        page_number = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        paginator = Paginator(queryset.order_by('-date_created'), page_size)
        page_obj = paginator.get_page(page_number)
        serializer = UserSerializer(page_obj, many=True)

        return Response({
            'results': serializer.data,
            'pagination': {
                'total': queryset.count(),
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        try:
            organization = request.organization
            user = self.get_queryset().filter(
                is_active=True, organization_users__organization=organization).get(id=pk)
            serializer = UserSerializer(user)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.data, status=status.HTTP_200_OK)


@add_swagger_to_groups_view
class GroupsView(viewsets.GenericViewSet):
    serializer_class = GroupSerializer
    queryset = AppGroup.objects.select_related('organization')

    def get_permissions(self):
        permissions = {
            'create': CREATE_GROUPS_AND_ROLES,
            'update': UPDATE_GROUPS_AND_ROLES,
            'destroy': DELETE_GROUPS_AND_ROLES,
            'list': VIEW_GROUPS_AND_ROLES,
        }
        user_permission = permissions[self.action]
        print(f'user: {self.request.user}'
              f' permission to check:{user_permission}')
        return [
            IsAuthenticated(), UserPermission(user_permission)
        ]

    def list(self, request, *args, **kwargs):
        groups = AppGroup.objects.prefetch_related('permissions').filter(
            Q(is_active=True, organization=request.organization) | Q(is_default=True)
        ).order_by('rank', 'name')

        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = GroupWithRankSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            group = serializer.save()
            return Response(self.get_serializer(group).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            group = AppGroup.objects.get(id=kwargs['pk'], organization=request.organization, is_active=True)
            serializer = GroupWithRankSerializer(instance=group, data=request.data, partial=True,
                                                 context={'request': request})
            if serializer.is_valid():
                group = serializer.save()
                return Response(self.get_serializer(group).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AppGroup.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        try:
            group = AppGroup.objects.get(id=kwargs['pk'], organization=request.organization, is_active=True)
            if group.user_set.exists():
                return Response({'error': 'Cannot delete a role with assigned users.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if group.is_default:
                return Response({'error': 'Default role cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)
            group.soft_delete(owner=request.user)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        except AppGroup.DoesNotExist:
            return Response({'error': 'Role could not be found'}, status=status.HTTP_404_NOT_FOUND)


@add_swagger_to_permission_list_view
class PermissionListView(views.APIView):
    """
    Retrieve all custom permissions, excluding Django's default permissions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch permissions our custom permissions. exlude the django default permissions
        permissions = AppPermission.objects.get_permissions()
        # Serialize and return the permissions
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
