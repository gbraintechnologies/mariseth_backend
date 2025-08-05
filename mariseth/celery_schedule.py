from datetime import timedelta

from celery.schedules import crontab
from decouple import config as env

queue = env('CELERY_DEFAULT_QUEUE')

CELERY_BEAT_SCHEDULES = {
    'update_overdue_credits': {
        'task': 'apps.shared.tasks.utils.update_overdue_credits',
        'schedule': crontab(minute=0, hour=0),
        'options': {
            'queue': queue
        }
    },
    'update_completed_leaves': {
        'task': 'apps.shared.tasks.utils.update_completed_leaves',
        'schedule': crontab(minute=0, hour=0),
        'options': {
            'queue': queue
        }
    }
}

CELERY_TASK_ROUTES_QUEUES = {
    '*': {'queue': queue}
}
