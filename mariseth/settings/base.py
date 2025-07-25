from pathlib import Path

import sentry_sdk
from decouple import config as env
from kombu import Queue
from sentry_sdk.integrations.django import DjangoIntegration

from mariseth.celery_schedule import CELERY_BEAT_SCHEDULES, CELERY_TASK_ROUTES_QUEUES
from mariseth.logging import LOGGERS

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env('SECRET_KEY')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third party apps
    'django_celery_beat',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'rest_framework_simplejwt.token_blacklist',
    'storages',
    'drf_yasg',
    'channels',

    # local apps
    'apps.accounts.apps.AccountsConfig',
    'apps.shared.apps.SharedConfig',
    'apps.organizations.apps.OrganizationsConfig',
    'apps.farm.apps.FarmConfig',
    'apps.credit.apps.CreditConfig',
    'apps.customers.apps.CustomersConfig',
    'apps.warehouse.apps.WarehouseConfig',
    'apps.inflow.apps.InflowConfig',
    'apps.outflow.apps.OutflowConfig',
    'apps.accounting.apps.AccountingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.shared.utils.organization_middleware.AddOrganizationMiddleware',
    'apps.shared.utils.current_user_middleware.CurrentUserMiddleware',

]

ROOT_URLCONF = 'mariseth.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mariseth.wsgi.application'
ASGI_APPLICATION = 'mariseth.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'ATOMIC_REQUESTS': True,
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

APPEND_SLASH = False

ENVIRONMENT = env('ENVIRONMENT')

STATIC_URL = 'static/'

STORAGES = {
    "default": {"BACKEND": "apps.shared.overrides.MediaRootS3Boto3Storage"},
    "staticfiles": {"BACKEND": "apps.shared.overrides.StaticRootS3Boto3Storage"},
}

CORS_ALLOWED_ORIGINS = [
    'https://local.iyfconnect.com',
    'http://localhost:8000',
    'http://0.0.0.0:8000',
    'http://127.0.0.1:0000',
    'https://ukskccsc0cwwo4cockkkks4w.135.181.238.146.sslip.io',
]

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [

        'rest_framework.throttling.AnonRateThrottle',

        'rest_framework.throttling.UserRateThrottle'

    ],
    'DEFAULT_THROTTLE_RATES': {

        'anon': '60/min',

        'user': '120/min'

    },
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'apps.shared.utils.renderer.CustomJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

INTERNAL_HOST = env('INTERNAL_HOST')

LOGGING = LOGGERS

CELERY_BROKER_URL = env("CELERY_BROKER_URL")

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE = CELERY_BEAT_SCHEDULES

CELERY_DEFAULT_QUEUE = env('CELERY_DEFAULT_QUEUE')
CELERY_QUEUES = (
    Queue(CELERY_DEFAULT_QUEUE),
)
CELERY_TASK_ROUTES = CELERY_TASK_ROUTES_QUEUES
CELERY_MAX_RETRIES = 3
CELERY_DEFAULT_RETRY_DELAY = 10

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [
                (
                    env('REDIS_HOST', 'redis'),  # Service name in Docker
                    int(env('REDIS_PORT', 6379))
                )
            ],
            'capacity': 1500,
            'expiry': 5
        },
    },
}
CHANNEL_REDIS_PREFIX = "socket:"

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    traces_sample_rate=1.0,
    _experiments={
        "continuous_profiling_auto_start": True,
    },
    profiles_sample_rate=1,
    environment=env('ENVIRONMENT'),
    integrations=[DjangoIntegration()]
)

EMAIL_PROVIDER = "sendgrid"
SENDGRID_API_KEY = env("SENDGRID_API_KEY")
SMS_PROVIDER = "wirepick"
WIREPICK_CLIENT_ID = env("WIREPICK_CLIENT_ID")
WIREPICK_PASSWORD = env("WIREPICK_PASSWORD")
WIREPICK_SENDER_ID = env("WIREPICK_SENDER_ID")

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'SECURITY_REQUIREMENTS': [
        {'Bearer': []}
    ],
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SHOW_REQUEST_HEADERS': True,
}