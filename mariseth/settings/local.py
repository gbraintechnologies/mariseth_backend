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
# AWS S3 configuration
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', None)
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', None)

CSRF_TRUSTED_ORIGINS = [
    "http://*",
    "https://*",
    "https://dwg0gwkko0w0kw0ccgogwo0c.135.181.238.146.sslip.io"
]
# extra static and media file settings.
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN')
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'


# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [{
#                 'address': (env('REDIS_HOST'), int(env('REDIS_PORT', default=6379))),
#                 'db': 0,
#             }],
#             'capacity': 1500,
#             'expiry': 5
#         },
#     },
# }
# CHANNEL_REDIS_PREFIX = "socket:"
