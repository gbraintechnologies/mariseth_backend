import os

from celery.schedules import crontab
from decouple import config as env

queue = env('CELERY_DEFAULT_QUEUE')

CELERY_BEAT_SCHEDULES = {

}

CELERY_TASK_ROUTES_QUEUES = {
    '*': {'queue': queue}
}
