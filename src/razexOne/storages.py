from storages.backends.s3boto3 import S3Boto3Storage
from razexOne.settings import (
    PUBLIC_MEDIA_LOCATION,
    PRIVATE_MEDIA_LOCATION,
)


class PublicMediaStorage(S3Boto3Storage):
    location = PUBLIC_MEDIA_LOCATION
    default_acl = "public-read"  # Public access
    file_overwrite = False


class PrivateMediaStorage(S3Boto3Storage):
    location = PRIVATE_MEDIA_LOCATION
    default_acl = "private"  # Private access
    file_overwrite = False
    custom_domain = False  # No public access
