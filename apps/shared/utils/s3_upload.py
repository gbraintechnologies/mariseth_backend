import boto3
from botocore.exceptions import NoCredentialsError

from django.conf import settings


def upload_to_s3(file_data, file_name):

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN

    try:
        print("Uploading to S3")
        if settings.ENVIRONMENT == 'local':
            s3 = boto3.client(
                's3',
                region_name=settings.AWS_S3_REGION_NAME,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        else:
            s3 = boto3.client('s3')
        s3.upload_fileobj(file_data, bucket_name, f"media/reports/{file_name}")
        s3_url = f'https://{custom_domain}/media/reports/{file_name}'
        print(s3_url)
        return s3_url
    except NoCredentialsError:
        return "Credentials not available"
