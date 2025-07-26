from django.core.validators import MinLengthValidator
from django.db import models

from apps.shared.models import BaseModel
from apps.shared.utils.validators import validate_only_digits


class Department(BaseModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=255, unique=True)
    department_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Active")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="departments"
    )

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobTitle(BaseModel):
    name = models.CharField(max_length=255)
    job_title_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    level = models.ForeignKey(
        "shared.CustomType", on_delete=models.SET_NULL, null=True, blank=True, related_name="job_title_levels",
    )
    department = models.ForeignKey("hr.Department", related_name="job_titles", on_delete=models.CASCADE)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="job_titles"
    )
    job_description_url = models.URLField(blank=True, null=True)
    probation = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Job Title"
        verbose_name_plural = "Job Titles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(BaseModel):
    EMP_STATUS = (('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'))
    GENDER = (('m', 'Male'), ('f', 'Female'))
    RELATIONSHIP_STATUS = (('single', 'Single'), ('married', 'Married'), ('widowed', 'Widowed'))

    employee_id = models.CharField(max_length=20, unique=True)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=10, choices=GENDER)
    relationship_status = models.CharField(max_length=20, choices=RELATIONSHIP_STATUS, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(unique=True, max_length=40, blank=False, null=True,
                                    validators=[
                                        MinLengthValidator(
                                            11, "Phone number number must be at least 11 characters."),
                                        validate_only_digits], )
    bank_account_number = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=EMP_STATUS, default='active')
    date_of_birth = models.DateField(null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="employees"
    )


class EmployeeEmergencyContact(BaseModel):
    employee = models.ForeignKey(Employee, related_name='emergency_contacts', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=40, blank=False, null=True,
                                    validators=[
                                        MinLengthValidator(
                                            11, "Phone number number must be at least 11 characters."),
                                        validate_only_digits], )


class EmployeeQualification(BaseModel):
    employee = models.ForeignKey(Employee, related_name='qualifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    certificate = models.FileField(upload_to='qualifications/', null=True, blank=True)


class EmployeeContract(BaseModel):
    CONTRACT_TYPES_CHOICES = (
        ('full_time', 'Full-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('part_time', 'Part-Time')
    )
    WORK_TYPES = (
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('on_site', 'On-site')
    )
    employee = models.OneToOneField('Employee', on_delete=models.CASCADE, related_name='contract')
    start_date = models.DateField()  # Employment Start Date
    job_title = models.ForeignKey('JobTitle', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='employees')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='employees')
    employment_type = models.CharField(max_length=20, choices=CONTRACT_TYPES_CHOICES)
    work_type = models.CharField(max_length=20, choices=WORK_TYPES)
    annual_leave_days = models.PositiveIntegerField(default=0)
    sick_leave_days = models.PositiveIntegerField(default=0)
    leave_rollover = models.BooleanField(default=False)


class EmployeeDisciplinaryAction(BaseModel):
    ACTION_TYPES = (('warning', 'Warning'), ('suspension', 'Suspension'), ('dismissal', 'Dismissal'))

    employee = models.ForeignKey(Employee, related_name='disciplinary_actions', on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    offence = models.TextField()
    date_issued = models.DateField(auto_now_add=True)
    comments = models.TextField(null=True, blank=True)
