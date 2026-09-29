"""S3 object storage (SeaweedFS) — immutable originals (D04).

Rules enforced here (Principle 2 — Immutable Evidence):
- originals are stored under originals/<uuid>/<filename> and never overwritten
  (an existing object_key raises before any write)
- every upload is hashed (SHA-256) and the hash recorded
"""
import hashlib
import os
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://s3:8333"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "any"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "unused"),
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return os.environ.get("S3_BUCKET", "litigation-evidence")


def ensure_bucket() -> None:
    c = _client()
    try:
        c.head_bucket(Bucket=_bucket())
    except ClientError:
        c.create_bucket(Bucket=_bucket())


def put_original(data: bytes, filename: str, mime_type: str) -> tuple[str, str]:
    """Store an original; returns (object_key, sha256). Refuses overwrite."""
    sha = hashlib.sha256(data).hexdigest()
    key = f"originals/{uuid.uuid4()}/{filename}"
    c = _client()
    # overwrite guard: key is brand new (uuid), belt-and-braces check anyway
    try:
        c.head_object(Bucket=_bucket(), Key=key)
        raise RuntimeError(f"object already exists at {key} — refusing to overwrite original")
    except ClientError as e:
        if e.response["ResponseMetadata"]["HTTPStatusCode"] not in (404,):
            raise
    c.put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=mime_type)
    return key, sha


def get_bytes(object_key: str) -> bytes:
    return _client().get_object(Bucket=_bucket(), Key=object_key)["Body"].read()


def presigned_url(object_key: str, expires: int = 300) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": object_key},
        ExpiresIn=expires,
    )
