from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import Settings
from app.ingestion.errors import IngestionError


class LocalSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(
        self,
        storage_key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        del content_type
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise IngestionError(
                "invalid_storage_key",
                "snapshot storage key must stay inside the configured root",
                retryable=False,
            )

        target = self.root.joinpath(*key.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise IngestionError(
                    "snapshot_collision",
                    "content-addressed snapshot key contains different bytes",
                    retryable=False,
                )
            return

        with NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)


class S3Client(Protocol):
    def head_bucket(self, **kwargs: object) -> dict[str, object]: ...

    def create_bucket(self, **kwargs: object) -> dict[str, object]: ...

    def head_object(self, **kwargs: object) -> dict[str, object]: ...

    def put_object(self, **kwargs: object) -> dict[str, object]: ...


class S3SnapshotStore:
    def __init__(self, *, client: S3Client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> "S3SnapshotStore":
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        store = cls(client=client, bucket=settings.s3_bucket)
        if settings.s3_auto_create_bucket:
            store.ensure_bucket(region=settings.s3_region)
        return store

    def ensure_bucket(self, *, region: str) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise IngestionError(
                    "object_store_unavailable",
                    "could not inspect the snapshot bucket",
                    retryable=True,
                ) from error

        arguments: dict[str, object] = {"Bucket": self.bucket}
        if region != "us-east-1":
            arguments["CreateBucketConfiguration"] = {"LocationConstraint": region}
        try:
            self.client.create_bucket(**arguments)
        except ClientError as error:
            raise IngestionError(
                "object_store_unavailable",
                "could not create the snapshot bucket",
                retryable=True,
            ) from error

    def put(
        self,
        storage_key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise IngestionError(
                "invalid_storage_key",
                "snapshot storage key must stay inside the configured bucket",
                retryable=False,
            )

        digest = sha256(content).hexdigest()
        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=storage_key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise IngestionError(
                    "object_store_unavailable",
                    "could not inspect the snapshot object",
                    retryable=True,
                ) from error
        else:
            metadata = existing.get("Metadata", {})
            existing_digest = metadata.get("sha256") if isinstance(metadata, dict) else None
            if existing_digest != digest:
                raise IngestionError(
                    "snapshot_collision",
                    "content-addressed snapshot key contains different bytes",
                    retryable=False,
                )
            return

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
                Metadata={"sha256": digest},
            )
        except ClientError as error:
            raise IngestionError(
                "object_store_unavailable",
                "could not persist the snapshot object",
                retryable=True,
            ) from error
