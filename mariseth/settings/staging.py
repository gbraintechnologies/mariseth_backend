from datetime import timedelta

from mariseth.settings.base import *


ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    "http://*",
    "https://*"
    "dwg0gwkko0w0kw0ccgogwo0c.135.181.238.146.sslip.io"
]
CORS_ALLOW_ALL_ORIGINS = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DEBUG = True
ENVIRONMENT = env('ENVIRONMENT')
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=120),
}
# extra static and media file settings.
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN')
# Static files (CSS, JavaScript, images)
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
# Media files
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
