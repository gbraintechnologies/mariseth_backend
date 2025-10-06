from datetime import timedelta

from mariseth.settings.base import *

ALLOWED_HOSTS = ['*']
ENVIRONMENT = env('ENVIRONMENT')
DEBUG = False

CORS_ALLOWED_ORIGINS = [
    "https://mariseth.scaleforge.farm",
    "https://v48ws000c8wg0gcgg880sg4o.65.109.122.43.sslip.io",
    "https://s4ckwk8g4cc88k8sgww084ko.65.109.122.43.sslip.io",
    "https://sw0k8ooc0cwws0wgg8kgcos8.65.109.108.54.sslip.io"
]

CSRF_TRUSTED_ORIGINS = [
    "http://*",
    "https://*",
    "https://backend.65.109.122.43.sslip.io"
]

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=120),
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
INTERNAL_HOST = env('INTERNAL_HOST')

STATIC_URL = '/static/'
STATICFILES_LOCATION = 'static'
STATICFILES_STORAGE = "blogs.storage.StaticS3Boto3Storage"

MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = "blogs.storage.S3MediaStorage"

AWS_ACCESS_KEY_ID = env('MINIO_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = env('MINIO_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = env('MINIO_BUCKET_NAME')

AWS_S3_ENDPOINT_URL = env('MINIO_ENDPOINT_URL')
MINIO_ACCESS_URL = env('MINIO_ENDPOINT_URL')
