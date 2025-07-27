from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import random
from django.db import transaction

from apps.hr.models import Department, JobTitle, Employee, EmployeeContract
from apps.hr.utils import generate_department_id, generate_employee_id
from apps.organizations.models import Organization
from apps.shared.models import CustomType

User = get_user_model()


class Command(BaseCommand):
    help = 'Populates the database with sample HR data: Departments, Job Titles, and Employees.'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Starting HR data population...'))

            try:
                # Get or create a default user for created_by fields
                admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True})
                if created:
                    admin_user.set_password('adminpassword') # Set a default password, change in production
                    admin_user.save()
                    self.stdout.write(self.style.WARNING('Created a default admin user. Please change the password in production.'))
                else:
                    self.stdout.write(self.style.SUCCESS('Using existing admin user.'))

                # Get or create a default organization
                organization = Organization.objects.get(pk=1)
                if created:
                    self.stdout.write(self.style.SUCCESS('Created a default organization.'))
                else:
                    self.stdout.write(self.style.SUCCESS('Using existing default organization.'))

                # 1. Create 5 Departments
                self.stdout.write(self.style.SUCCESS('Creating 5 Departments...'))
                departments = []
                for i in range(3, 6):
                    department = Department.objects.create(
                        name=f'Department {i}',
                        department_id=generate_department_id(organization.id, i),
                        description=f'Description for Department {i}',
                        organization=organization,
                        created_by=admin_user
                    )
                    departments.append(department)
                    self.stdout.write(self.style.SUCCESS(f'Created Department: {department.name}'))

                # 2. Create 10 Job Titles across these departments
                self.stdout.write(self.style.SUCCESS('Creating 10 Job Titles...'))
                job_titles = []
                for i in range(3, 11):
                    department = random.choice(departments)
                    job_title = JobTitle.objects.create(
                        name=f'Job Title {i}',
                        job_title_id=generate_department_id(organization.id, i),
                        level=CustomType.objects.get(pk=2),
                        department=department,
                        organization=organization,
                        created_by=admin_user
                    )
                    job_titles.append(job_title)
                    self.stdout.write(self.style.SUCCESS(f'Created Job Title: {job_title.name} in {department.name}'))

                # 3. Create 10 Employees using these job titles
                self.stdout.write(self.style.SUCCESS('Creating 10 Employees...'))
                employees = []
                for i in range(3, 11):
                    job_title = random.choice(job_titles)
                    employee = Employee.objects.create(
                        employee_id=generate_employee_id(organization.id, i),
                        first_name=f'Employee{i}FN',
                        last_name=f'Employee{i}LN',
                        email=f'employee{i}@example.com',
                        phone_number=f'+123456789{i:02d}',
                        date_of_birth='1990-01-01',
                        gender=random.choice([choice[0] for choice in Employee.GENDER]),
                        relationship_status=random.choice([choice[0] for choice in Employee.RELATIONSHIP_STATUS]),
                        bank_account_number=f'BANKACC{i:04d}',
                        status=random.choice([choice[0] for choice in Employee.EMP_STATUS]),
                        organization=organization,
                        created_by=admin_user
                    )
                    # Generate employee ID after creation to use employee.pk
                    employee.employee_id = generate_employee_id(employee.organization.id, employee.pk)
                    employee.save(update_fields=['employee_id'])
                    employees.append(employee)
                    self.stdout.write(self.style.SUCCESS(f'Created Employee: {employee.first_name} {employee.last_name} ({employee.employee_id})'))

                    # Create EmployeeContract for the employee
                    EmployeeContract.objects.create(
                        employee=employee,
                        start_date='2020-01-01',
                        job_title=job_title,
                        department=job_title.department,
                        employment_type=random.choice([choice[0] for choice in EmployeeContract.CONTRACT_TYPES_CHOICES]),
                        work_type=random.choice([choice[0] for choice in EmployeeContract.WORK_TYPES]),
                        annual_leave_days=random.randint(10, 20),
                        sick_leave_days=random.randint(5, 10),
                        leave_rollover=random.choice([True, False]),
                        created_by=admin_user
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created contract for Employee: {employee.first_name} {employee.last_name}'))

                self.stdout.write(self.style.SUCCESS('HR data population complete!'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
