from datetime import timedelta

from mariseth.settings.base import *

ALLOWED_HOSTS = ['*']

DEBUG = False

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=120),
}
# CSRF_TRUSTED_ORIGINS = [
#
# ]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
INTERNAL_HOST = env('INTERNAL_HOST')
CSRF_TRUSTED_ORIGINS = ['https://*.iyfconnect.app']
# extra static and media file settings.
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN')
# Static files (CSS, JavaScript, images)
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
# Media files
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
CORS_ALLOW_ALL_ORIGINS = True

