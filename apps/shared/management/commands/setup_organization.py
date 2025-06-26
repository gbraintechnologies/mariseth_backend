from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Organization, OrganizationUser


class Command(BaseCommand):
    help = 'Create organization setup with default branch and assign users'

    def handle(self, *args, **kwargs):
        if settings.ENVIRONMENT == 'production':
            return
        User = get_user_model()

        # Default users data
        default_superusers = [
            {'email': 'daniel@email.com', 'first_name': 'Daniel', 'last_name': 'Adu'},
            {'email': 'victor@email.com', 'first_name': 'Victor', 'last_name': 'Acheampong'},
            {'email': 'kenneth@email.com', 'first_name': 'Kenneth', 'last_name': 'Owusu'},
        ]

        try:
            with transaction.atomic():
                # Create organization
                organization, org_created = Organization.objects.get_or_create(
                    name="Mariseth Famrs",
                    defaults={
                        'address': 'Accra Ghana',
                    }
                )
                if org_created:
                    self.stdout.write(self.style.SUCCESS(f"Created organization: {organization.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Organization {organization.name} already exists"))

                # Create or get users and assign to organization
                for user_data in default_superusers:
                    user, user_created = User.objects.get_or_create(
                        email=user_data['email'],
                        defaults={
                            'username': user_data['email'],
                            'first_name': user_data['first_name'],
                            'last_name': user_data['last_name'],
                            'is_superuser': True,
                            'is_staff': True,
                            'is_active': True,
                            'is_verified': True,
                            'user_type': "admin",
                        }
                    )

                    if user_created:
                        user.set_password("password123")
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"Created user: {user.email}"))

                    # Create OrganizationUser if it doesn't exist
                    org_user, org_user_created = OrganizationUser.objects.get_or_create(
                        user=user,
                        organization=organization,
                    )

                    if org_user_created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created organization user: {user.email} - {organization.name}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Organization user already exists for: {user.email}"
                            )
                        )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during organization setup: {str(e)}")
            )
