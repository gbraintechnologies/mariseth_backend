from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Branch, Organization, OrganizationUser


class Command(BaseCommand):
    help = 'Create organization setup with default branch and assign users'

    def handle(self, *args, **kwargs):
        if settings.ENVIRONMENT == 'production':
            return
        User = get_user_model()

        # Default users data
        default_superusers = [
            {'email': 'dzifa@premierbank.com', 'first_name': 'Dzifa', 'last_name': 'Premier'},
            {'email': 'daniel@premierbank.com', 'first_name': 'Daniel', 'last_name': 'Premier'},
            {'email': 'patrick@premierbank.com', 'first_name': 'Patrick', 'last_name': 'Premier'},
            {'email': 'obed@premiertechlab.com', 'first_name': 'Obed', 'last_name': 'Premier'},
            {'email': 'kenneth@premierbank.com', 'first_name': 'Kenneth', 'last_name': 'Premier'},
            {'email': 'banabas@premierbank.com', 'first_name': 'Banabas', 'last_name': 'Premier'},
        ]

        # Branch data
        branches_data = [
            {
                'name': 'Premier Headquarters',
                'location': 'Accra',
                'address': 'Esiama Western Region'
            },
        ]

        try:
            with transaction.atomic():
                # Create organization
                organization, org_created = Organization.objects.get_or_create(
                    name="Premier Bank",
                    defaults={
                        'address': 'Accra Ghana',
                    }
                )
                if org_created:
                    self.stdout.write(self.style.SUCCESS(f"Created organization: {organization.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Organization {organization.name} already exists"))

                # Create all branches
                created_branches = []
                for branch_data in branches_data:
                    branch, branch_created = Branch.objects.get_or_create(
                        name=branch_data['name'],
                        defaults={
                            'location': branch_data['location'],
                            'address': branch_data['address'],
                            'is_default': True
                        }
                    )
                    created_branches.append(branch)

                    if branch_created:
                        self.stdout.write(self.style.SUCCESS(f"Created branch: {branch.name}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Branch {branch.name} already exists"))

                    if branch not in organization.branches.all():
                        organization.branches.add(branch)

                default_branch = next(
                    (branch for branch in created_branches if branch.name == 'Headquarters'),
                    created_branches[0]
                )

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
                            'user_type': 'admin',
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
                        defaults={
                            'branch': default_branch,
                        }
                    )

                    if org_user_created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created organization user: {user.email} - {organization.name} - {default_branch.name}"
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