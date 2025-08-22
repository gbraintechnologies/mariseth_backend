import boto3
from botocore.exceptions import NoCredentialsError

from django.conf import settings


def upload_to_s3(file_data, file_name):

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    try:
        print("Uploading to MinIO")
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=boto3.session.Config(signature_version="s3v4"),
            verify=False,  # This might be needed for self-signed certs in local MinIO setups
        )
        s3.upload_fileobj(file_data, bucket_name, f"media/reports/{file_name}")
        s3_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": f"media/reports/{file_name}"},
            ExpiresIn=86400,  # URL expires in 24 hours
        )
        print(s3_url)
        return s3_url
    except NoCredentialsError:
        return "Credentials not available"
