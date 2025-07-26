
def generate_department_id(organization_id, department_pk):
    return f"D-{organization_id}00{department_pk}"


def generate_job_title_id(organization_id, job_title_pk):
    return f"P-{organization_id}00{job_title_pk}"


def generate_employee_id(organization_id: int, employee_pk: int) -> str:
    return f"EMP-{organization_id}00{employee_pk}"
