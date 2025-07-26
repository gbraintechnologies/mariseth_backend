from django.contrib import admin

from apps.hr.models import Department, Employee, EmployeeContract, EmployeeDisciplinaryAction, EmployeeEmergencyContact, \
    EmployeeQualification, JobTitle


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


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "department_id", "status", "organization", "is_active")
    search_fields = ("name", "department_id")
    list_filter = ("status", "is_active", "organization")


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title_id", "level", "department", "organization", "is_active")
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
    ]
