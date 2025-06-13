from datetime import timedelta

from mariseth.settings.base import *

DEBUG = env('DEBUG', cast=bool)
# ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='*', cast=Csv())
ALLOWED_HOSTS = ["*"]
ENVIRONMENT = env('ENVIRONMENT')
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=120),
}
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://ukskccsc0cwwo4cockkkks4w.135.181.238.146.sslip.io"
]
CSRF_TRUSTED_ORIGINS = [
    "http://*",
    "https://*",
    "https://dwg0gwkko0w0kw0ccgogwo0c.135.181.238.146.sslip.io"
]
# # MinIO Configuration
# MINIO_ENDPOINT = env('MINIO_ENDPOINT_URL')  # e.g. http://minio:9000
# MINIO_BUCKET = env('MINIO_BUCKET_NAME')
#
# AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
# AWS_ACCESS_KEY_ID = env('MINIO_ACCESS_KEY')
# AWS_SECRET_ACCESS_KEY = env('MINIO_SECRET_KEY')
# AWS_STORAGE_BUCKET_NAME = MINIO_BUCKET
# AWS_S3_SIGNATURE_VERSION = 's3v4'
# AWS_S3_ADDRESSING_STYLE = 'path'  # Crucial for MinIO
# AWS_S3_USE_SSL = False
# AWS_S3_VERIFY = False
#
# # URL Configuration (FIXED)
# STATIC_URL = f'{MINIO_ENDPOINT}/{MINIO_BUCKET}/static/'
# MEDIA_URL = f'{MINIO_ENDPOINT}/{MINIO_BUCKET}/media/'


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
