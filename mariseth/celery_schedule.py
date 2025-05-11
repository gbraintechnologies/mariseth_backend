from datetime import timedelta

from decouple import config as env

queue = env('CELERY_DEFAULT_QUEUE')

CELERY_BEAT_SCHEDULES = {
    'update_overdue_credits': {
        'task': 'apps.shared.tasks.email_tasks.update_overdue_credits',
        'schedule': timedelta(minutes=1),
        'options': {
            'queue': queue
        }
    },
}

CELERY_TASK_ROUTES_QUEUES = {
    '*': {'queue': queue}
}
