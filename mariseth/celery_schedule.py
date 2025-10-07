
from celery.schedules import crontab
from decouple import config as env

queue = env('CELERY_DEFAULT_QUEUE')

CELERY_BEAT_SCHEDULES = {
    'retry_failed_integrations': {
        'task': 'apps.shared.tasks.scheduler_tasks.retry_failed_integrations',
        'schedule': crontab(minute='*/30'),
        'options': {
            'queue': queue
        }
    },
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
