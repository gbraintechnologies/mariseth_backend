from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove old customer permissions and improperly named delete_customer permissions."

    def handle(self, *args, **kwargs):
        # Define codenames to remove (only those without 'customer|' prefix)
        target_codenames = [
            "list_customers",
            "update_customer",
            "create_customer",
        ]

        # Query and delete those permissions
        deleted_count = 0
        for codename in target_codenames:
            perms = Permission.objects.filter(codename=codename).exclude(codename__startswith="customer|")
            count = perms.count()
            perms.delete()
            deleted_count += count
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} permission(s) with codename '{codename}'"))

        # Delete any delete_customer permission without 'customer|' prefix
        delete_perms = Permission.objects.filter(codename="delete_customer").exclude(codename__startswith="customer|")
        count = delete_perms.count()
        delete_perms.delete()
        deleted_count += count
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {count} permission(s) with codename 'delete_customer' not starting with 'customer|'"))

        self.stdout.write(self.style.SUCCESS(f"Total permissions deleted: {deleted_count}"))
