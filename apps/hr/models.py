from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.db import models

from apps.shared.models import BaseModel
from apps.shared.utils.validators import validate_only_digits

User = get_user_model()


class Department(BaseModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=255, unique=True)
    department_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
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
    EMP_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('dismissed', 'Dismissed'),
    )
    GENDER = (('m', 'Male'), ('f', 'Female'))
    RELATIONSHIP_STATUS = (('single', 'Single'), ('married', 'Married'), ('widowed', 'Widowed'))
    NOTIFICATION_CHOICES = (('email', 'Email'), ('sms', 'SMS'))

    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=10, choices=GENDER)
    relationship_status = models.CharField(max_length=20, choices=RELATIONSHIP_STATUS, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
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
    notification = models.CharField(max_length=20, choices=NOTIFICATION_CHOICES, default='email')

    def __str__(self):
        return f"{self.id} - {self.first_name} {self.last_name}"


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
    ssnit_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_branch = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=100, null=True, blank=True)
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


class LeaveType(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="leave_types"
    )
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    max_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum allowed days per year (null = unlimited)"
    )
    deducts_from_allowance = models.BooleanField(
        default=True,
        help_text="Whether this leave type deducts from employee's leave allowance"
    )
    deduct_from = models.CharField(
        max_length=20,
        choices=[('annual', 'Annual Leave'), ('sick', 'Sick Leave')],
        default='annual'
    )


class LeaveRequest(BaseModel):
    LEAVE_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Rejected'),
        ('canceled', 'Canceled'),
        ('completed', 'Completed')
    )
    leave_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="leave_requests"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_days = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    action_taken_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='action_leave_requests'
    )
    action_taken_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_created']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F('start_date')),
                name="end_after_start"
            )
        ]


class Training(BaseModel):
    TRAINING_TYPES = (
        ('internal', 'Internal'),
        ('external', 'External'),
    )
    TRAINING_MODES = (
        ('online', 'online'),
        ('offline', 'Offline'),
    )
    ATTENDANCE_STATUS = (
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    )
    training_id = models.CharField(max_length=20, unique=True)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="trainings"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    training_type = models.CharField(max_length=20, choices=TRAINING_TYPES)
    training_mode = models.CharField(max_length=20, choices=TRAINING_MODES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True, null=True)
    material_url = models.URLField(blank=True, null=True)
    all_employees = models.BooleanField(default=False)
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='ongoing')

    def __str__(self):
        return f"{self.id} - {self.title} ({self.training_id})"

    @property
    def attendees(self):
        return TrainingAttendee.objects.filter(training=self)

    @property
    def attendee_count(self):
        return self.attendees.count()

    @property
    def present_count(self):
        return self.attendees.filter(status='present').count()

    @property
    def attendance_rate(self):
        return round((self.present_count / self.attendee_count * 100), 1) if self.attendee_count else 0

    @property
    def get_all_employees_display(self):
        return "Yes" if self.all_employees else "No"


class TrainingAttendee(BaseModel):
    ATTENDANCE_STATUS = (
        ('present', 'Present'),
        ('absent', 'Absent'),
    )
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='training_attendances')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_attendances')
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='absent')
    marked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('training', 'employee')
        verbose_name_plural = 'Training Attendances'

    def __str__(self):
        return f"{self.employee} - {self.training} - {self.status}"
