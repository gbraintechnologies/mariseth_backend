from django.contrib import admin

from apps.hr.models import Department, Employee, EmployeeContract, EmployeeDisciplinaryAction, EmployeeEmergencyContact, \
    EmployeeQualification, JobTitle, Training, TrainingAttendee, LeaveType, LeaveRequest


class EmergencyContactInline(admin.StackedInline):
    model = EmployeeQualification
    extra = 1


class QualificationInline(admin.StackedInline):
    model = EmployeeEmergencyContact
    extra = 1


class EmployeeContractInline(admin.StackedInline):
    model = EmployeeContract
    extra = 1


class EmployeeDisciplinaryActionInline(admin.StackedInline):
    model = EmployeeDisciplinaryAction
    extra = 1


class TrainingAttendeeInline(admin.TabularInline):
    model = TrainingAttendee
    extra = 1
    fields = ('employee', 'status', 'marked_at')
    raw_id_fields = ('employee',)


class LeaveRequestInline(admin.TabularInline):
    model = LeaveRequest
    extra = 1
    fields = ('leave_type', 'start_date', 'end_date', 'leave_days', 'status', 'rejection_reason')
    raw_id_fields = ('employee', 'leave_type')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', "name", "department_id", "status", "organization", "is_active")
    search_fields = ("name", "department_id")
    list_filter = ("status", "is_active", "organization")


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ('id', "name", "job_title_id", "level", "department", "organization", "is_active")
    search_fields = ("name", "job_title_id")
    list_filter = ("level", "department", "is_active", "organization")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "first_name", "last_name", "email",
                    "phone_number", "status", "organization", "is_active")
    search_fields = ("employee_id", "first_name", "last_name", "email",
                     "phone_number")
    list_filter = ("gender", "relationship_status", "status", "organization",
                   "is_active")
    inlines = [
        EmergencyContactInline,
        QualificationInline,
        EmployeeContractInline,
        EmployeeDisciplinaryActionInline,
        LeaveRequestInline,
    ]


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'training_id', 'training_type', 'training_mode', 'start_date', 'end_date', 'organization',
        'is_active')
    search_fields = ('title', 'training_id', 'location')
    list_filter = ('training_type', 'training_mode', 'is_active', 'organization')
    inlines = [
        TrainingAttendeeInline,
    ]
    fieldsets = (
        (None, {
            'fields': (
                'title', 'description', 'training_type',
                'training_mode', 'start_date', 'end_date',
                'location', 'material_url', 'organization',
                'all_employees', 'is_active'
            )
        }),
    )
    readonly_fields = ('training_id',)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'max_days', 'deducts_from_allowance', 'deduct_from', 'is_active')
    search_fields = ('name',)
    list_filter = ('deducts_from_allowance', 'deduct_from', 'is_active')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'leave_id', 'employee', 'leave_type', 'start_date', 'end_date', 'leave_days', 'status', 'is_active')
    search_fields = ('leave_id', 'employee__first_name', 'employee__last_name', 'leave_type__name')
    list_filter = ('status', 'leave_type', 'is_active')
    raw_id_fields = ('employee', 'leave_type')
    readonly_fields = ('leave_id',)
    fieldsets = (
        (None, {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'leave_days', 'reason', 'status', 'rejection_reason', 'organization')
        }),
    )