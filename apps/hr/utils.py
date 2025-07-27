
def generate_department_id(organization_id, department_pk):
    return f"D-{organization_id}00{department_pk}"


def generate_job_title_id(organization_id, job_title_pk):
    return f"P-{organization_id}00{job_title_pk}"


def generate_employee_id(organization_id: int, employee_pk: int) -> str:
    return f"EMP-{organization_id}00{employee_pk}"


def generate_leave_id(leave_request) -> str:
    year = leave_request.date_created.strftime('%y')
    employee_initials = f"{leave_request.employee.first_name[0]}{leave_request.employee.last_name[0]}".upper()
    return f"LR-{year}-{employee_initials}{leave_request.pk}"


def generate_training_id(organization_id: int, training_pk: int) -> str:
    return f"TR-{organization_id}00{training_pk}"
