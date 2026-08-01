from hashlib import sha256
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from app.ingestion.errors import IngestionError
from app.ingestion.stores import S3SnapshotStore


def missing(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "missing"}}, operation)


class FakeS3Client:
    def __init__(self) -> None:
        self.bucket_exists = False
        self.objects: dict[str, dict[str, object]] = {}
        self.put_calls = 0
        self.create_arguments: dict[str, object] | None = None

    def head_bucket(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        if not self.bucket_exists:
            raise missing("404", "HeadBucket")
        return {}

    def create_bucket(self, **kwargs: object) -> dict[str, object]:
        self.bucket_exists = True
        self.create_arguments = dict(kwargs)
        return {}

    def head_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise missing("NoSuchKey", "HeadObject")
        return self.objects[key]

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.put_calls += 1
        self.objects[str(kwargs["Key"])] = {
            "Metadata": dict(kwargs["Metadata"]),
            "Body": kwargs["Body"],
            "ContentType": kwargs["ContentType"],
        }
        return {}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        stored = self.objects.get(str(kwargs["Key"]))
        if stored is None:
            raise missing("NoSuchKey", "GetObject")
        return {
            "Metadata": stored["Metadata"],
            "Body": BytesIO(stored["Body"]),
        }


def test_s3_store_creates_a_missing_development_bucket() -> None:
    client = FakeS3Client()
    store = S3SnapshotStore(client=client, bucket="evidence")

    store.ensure_bucket(region="us-east-1")

    assert client.bucket_exists is True
    assert client.create_arguments == {"Bucket": "evidence"}


def test_s3_store_is_idempotent_for_identical_content() -> None:
    client = FakeS3Client()
    store = S3SnapshotStore(client=client, bucket="evidence")
    content = b"immutable evidence"

    store.put("sources/source/snapshot.bin", content, content_type="text/plain")
    store.put("sources/source/snapshot.bin", content, content_type="text/plain")

    assert client.put_calls == 1
    assert client.objects["sources/source/snapshot.bin"] == {
        "Metadata": {"sha256": sha256(content).hexdigest()},
        "Body": content,
        "ContentType": "text/plain",
    }
    assert store.get("sources/source/snapshot.bin") == content


def test_s3_store_rejects_content_address_collisions() -> None:
    client = FakeS3Client()
    client.objects["sources/source/snapshot.bin"] = {
        "Metadata": {"sha256": "0" * 64}
    }
    store = S3SnapshotStore(client=client, bucket="evidence")

    with pytest.raises(IngestionError, match="different bytes"):
        store.put("sources/source/snapshot.bin", b"different")
