import os
import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class BucketHandlerError(Exception):
    pass


class BucketHandler:
    def __init__(self) -> None:
        self._endpoint = os.environ.get("S3_ENDPOINT")
        self._access_key = os.environ.get("S3_ACCESS_KEY")
        self._secret_key = os.environ.get("S3_SECRET_KEY")
        self._bucket = os.environ.get("S3_BUCKET_NAME")

        if not all([self._access_key, self._secret_key, self._bucket]):
            raise BucketHandlerError(
                "Missing required environment variables: "
                "S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME"
            )

        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint or None,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )



    def _build_key(self, filename: str) -> str:
        unique_id = uuid.uuid4().hex
        safe_name = filename.replace(" ", "_")
        return f"uploads/{unique_id}_{safe_name}"

    def _build_public_url(self, key: str) -> str:
        if self._endpoint:
            return f"{self._endpoint.rstrip('/')}/{self._bucket}/{key}"
        return f"https://{self._bucket}.s3.amazonaws.com/{key}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_file(self, file: BinaryIO, filename: str, content_type: str) -> str:
        """Upload a file-like object to the bucket. Returns the public URL."""
        key = self._build_key(filename)
        try:
            self._client.upload_fileobj(
                file,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except (BotoCoreError, ClientError) as exc:
            raise BucketHandlerError(f"Failed to upload file '{filename}': {exc}") from exc
        return self._build_public_url(key)

    def upload_bytes(self, data: bytes, filename: str, content_type: str) -> str:
        """Upload raw bytes to the bucket. Returns the public URL."""
        key = self._build_key(filename)
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise BucketHandlerError(f"Failed to upload bytes for '{filename}': {exc}") from exc
        return self._build_public_url(key)

    def get_file_url(self, filename: str) -> str:
        """Return the public URL for an already-stored file by its full key or bare name."""
        key = filename if filename.startswith("uploads/") else f"uploads/{filename}"
        return self._build_public_url(key)

    def delete_file(self, filename: str) -> bool:
        """Delete a file from the bucket. Returns True on success, False otherwise."""
        key = filename if filename.startswith("uploads/") else f"uploads/{filename}"
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except (BotoCoreError, ClientError):
            return False

