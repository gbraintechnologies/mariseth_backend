from datetime import timedelta

from mariseth.settings.base import *

frontend = env('FRONTEND_URL')
ALLOWED_HOSTS = ['*']
CORS_ALLOWED_ORIGINS = [
    frontend,
    "https://mariseth-staging.135.181.238.146.sslip.io"
]
CSRF_TRUSTED_ORIGINS = [
    "http://*",
    "https://*",
    "https://backend-staging.135.181.238.146.sslip.io"
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DEBUG = True
ENVIRONMENT = env('ENVIRONMENT')
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=120),
}
# extra static and media file settings.
# AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN')
# # Static files (CSS, JavaScript, images)
# STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
# # Media files
# MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

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