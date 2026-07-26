"""Private, immutable artifact object adapters for KMFA S05/P5.2.

The legacy filesystem adapter remains the default and the permanent read path
for existing v1.5 objects.  The S3-compatible adapter is enabled only by a
complete explicit environment configuration.  It never creates public URLs,
never derives keys from user filenames and uses one non-reusable key per
application artifact version.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

LEGACY_FILESYSTEM_MODE = "legacy-filesystem"
S3_COMPATIBLE_MODE = "s3"
LEGACY_STORAGE_BACKEND = "legacy-private-filesystem"
S3_STORAGE_BACKEND = "s3-compatible-private-v1"
DEFAULT_S3_PREFIX = "kmfa/private/v1"
LEGACY_LIFECYCLE_DELETE_ENV = (
    "KMFA_LIFECYCLE_ALLOW_LEGACY_FILESYSTEM_DELETE"
)
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
INTERNAL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_INSECURE_HOSTS = frozenset(
    {"127.0.0.1", "::1", "localhost", "object-store"}
)


class ObjectStorageError(RuntimeError):
    """Base error with a deliberately non-sensitive message."""


class ObjectStorageConfigurationError(ObjectStorageError):
    pass


class ObjectStorageUnavailableError(ObjectStorageError):
    pass


class ObjectStorageConflictError(ObjectStorageError):
    pass


class ObjectStorageMissingError(ObjectStorageError):
    pass


class ObjectStorageIntegrityError(ObjectStorageError):
    pass


@dataclass(frozen=True)
class PutObjectReceipt:
    storage_backend: str
    storage_key: str
    etag: str | None
    provider_version_id: str | None


@dataclass(frozen=True)
class MaterializedObject:
    path: Path
    temporary: bool


@dataclass(frozen=True)
class InventoryObject:
    storage_key: str
    size_bytes: int
    sha256: str
    metadata_sha256: str | None
    artifact_id: str | None
    artifact_version_id: str | None
    etag: str | None
    provider_version_id: str | None


@dataclass(frozen=True)
class S3ObjectStorageConfig:
    endpoint_url: str
    bucket: str
    region: str
    prefix: str
    access_key_id: str
    secret_access_key: str
    addressing_style: str
    verify_tls: bool

    @classmethod
    def from_environment(
        cls,
        *,
        access_key_env: str = "KMFA_S3_ACCESS_KEY_ID",
        secret_key_env: str = "KMFA_S3_SECRET_ACCESS_KEY",
    ) -> "S3ObjectStorageConfig":
        endpoint_url = os.environ.get("KMFA_S3_ENDPOINT_URL", "").strip()
        bucket = os.environ.get("KMFA_S3_BUCKET", "").strip()
        region = os.environ.get("KMFA_S3_REGION", "auto").strip()
        prefix = os.environ.get("KMFA_S3_PREFIX", DEFAULT_S3_PREFIX).strip()
        access_key_id = os.environ.get(access_key_env, "").strip()
        secret_access_key = os.environ.get(secret_key_env, "")
        addressing_style = os.environ.get(
            "KMFA_S3_ADDRESSING_STYLE", "path"
        ).strip()
        allow_insecure = (
            os.environ.get("KMFA_S3_ALLOW_INSECURE_LOCAL", "0").strip().lower()
            in TRUE_VALUES
        )

        if not all(
            (
                endpoint_url,
                bucket,
                region,
                prefix,
                access_key_id,
                secret_access_key,
            )
        ):
            raise ObjectStorageConfigurationError("invalid_s3_configuration")
        if BUCKET_RE.fullmatch(bucket) is None:
            raise ObjectStorageConfigurationError("invalid_s3_configuration")
        if addressing_style not in {"path", "virtual"}:
            raise ObjectStorageConfigurationError("invalid_s3_configuration")

        parsed = urlsplit(endpoint_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ObjectStorageConfigurationError("invalid_s3_configuration")
        if parsed.scheme == "http":
            hostname = parsed.hostname.lower()
            allowed_local = (
                hostname in ALLOWED_INSECURE_HOSTS
                or hostname.endswith(".localhost")
            )
            if not allow_insecure or not allowed_local:
                raise ObjectStorageConfigurationError("invalid_s3_configuration")

        normalized_prefix = prefix.strip("/")
        segments = normalized_prefix.split("/")
        if (
            not normalized_prefix
            or any(segment in {"", ".", ".."} for segment in segments)
            or any(
                re.fullmatch(r"[A-Za-z0-9._-]+", segment) is None
                for segment in segments
            )
        ):
            raise ObjectStorageConfigurationError("invalid_s3_configuration")

        return cls(
            endpoint_url=endpoint_url.rstrip("/"),
            bucket=bucket,
            region=region,
            prefix=normalized_prefix,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            addressing_style=addressing_style,
            verify_tls=parsed.scheme == "https",
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_file(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
) -> None:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if size != expected_size or digest.hexdigest() != expected_sha256:
        raise ObjectStorageIntegrityError("object_integrity_failed")


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _validate_internal_id(value: str) -> None:
    if INTERNAL_ID_RE.fullmatch(value) is None:
        raise ObjectStorageConfigurationError("invalid_object_identity")


def _validate_sha256(value: str) -> None:
    if SHA256_RE.fullmatch(value) is None:
        raise ObjectStorageConfigurationError("invalid_object_identity")


class FilesystemObjectStore:
    storage_backend = LEGACY_STORAGE_BACKEND
    public_label = "private-filesystem-volume-adapter"
    application_versioning = False

    def __init__(self, state_root: Path) -> None:
        self.state_root = state_root
        self.objects_dir = state_root / "objects"
        self.tmp_dir = state_root / "tmp"

    def ensure_ready(self) -> None:
        for path in (self.state_root, self.objects_dir, self.tmp_dir):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.chmod(0o700)

    def build_storage_key(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
        artifact_version_id: str,
        version_number: int,
        sha256: str,
    ) -> str:
        del workspace_id, artifact_id, artifact_version_id, version_number, sha256
        return f"{secrets.token_urlsafe(24)}.blob"

    def put_file(
        self,
        source_path: Path,
        *,
        storage_key: str,
        size_bytes: int,
        sha256: str,
        content_md5: str,
        artifact_id: str,
        artifact_version_id: str,
    ) -> PutObjectReceipt:
        del content_md5, artifact_id, artifact_version_id
        self.ensure_ready()
        if "/" in storage_key or "\\" in storage_key:
            raise ObjectStorageConfigurationError("invalid_object_identity")
        target = (self.objects_dir / storage_key).resolve()
        if target.parent != self.objects_dir.resolve():
            raise ObjectStorageConfigurationError("invalid_object_identity")
        try:
            os.link(source_path, target)
        except FileExistsError as exc:
            raise ObjectStorageConflictError("immutable_object_exists") from exc
        except OSError as exc:
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc
        try:
            target.chmod(0o600)
            _verify_file(
                target,
                expected_size=size_bytes,
                expected_sha256=sha256,
            )
            _fsync_directory(self.objects_dir)
            source_path.unlink()
        except Exception:
            _safe_unlink(target)
            raise
        return PutObjectReceipt(
            storage_backend=self.storage_backend,
            storage_key=storage_key,
            etag=None,
            provider_version_id=None,
        )

    def materialize_verified(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
    ) -> MaterializedObject:
        self.ensure_ready()
        candidate = (self.objects_dir / storage_key).resolve()
        if candidate.parent != self.objects_dir.resolve() or not candidate.is_file():
            raise ObjectStorageMissingError("object_missing")
        _verify_file(
            candidate,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        return MaterializedObject(path=candidate, temporary=False)

    def verify_existing(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
        artifact_id: str,
        artifact_version_id: str,
    ) -> PutObjectReceipt:
        """Resolve an ambiguous create without overwriting or deleting bytes."""

        del artifact_id, artifact_version_id
        self.materialize_verified(
            storage_key=storage_key,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        return PutObjectReceipt(
            storage_backend=self.storage_backend,
            storage_key=storage_key,
            etag=None,
            provider_version_id=None,
        )

    def delete_all_versions(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
        artifact_id: str,
        artifact_version_id: str,
        missing_is_success: bool,
    ) -> int:
        """Delete one verified legacy object for the isolated worker."""

        del artifact_id, artifact_version_id
        self.ensure_ready()
        if "/" in storage_key or "\\" in storage_key:
            raise ObjectStorageConfigurationError("invalid_object_identity")
        target = (self.objects_dir / storage_key).resolve()
        if target.parent != self.objects_dir.resolve():
            raise ObjectStorageConfigurationError("invalid_object_identity")
        if not target.exists():
            if missing_is_success:
                return 0
            raise ObjectStorageMissingError("object_missing")
        if target.is_symlink() or not target.is_file():
            raise ObjectStorageIntegrityError("object_integrity_failed")
        _verify_file(
            target,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        try:
            target.unlink()
            _fsync_directory(self.objects_dir)
        except OSError as exc:
            raise ObjectStorageUnavailableError(
                "object_store_unavailable"
            ) from exc
        if target.exists():
            raise ObjectStorageUnavailableError("object_store_unavailable")
        return 1


def _build_s3_client(config: S3ObjectStorageConfig):
    return boto3.session.Session().client(
        "s3",
        endpoint_url=config.endpoint_url,
        region_name=config.region,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        verify=config.verify_tls,
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=15,
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": config.addressing_style},
        ),
    )


def _client_error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def _etag(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.strip('"')


class S3ObjectStore:
    storage_backend = S3_STORAGE_BACKEND
    public_label = "private-s3-compatible-object-adapter"
    application_versioning = True

    def __init__(self, state_root: Path, config: S3ObjectStorageConfig) -> None:
        self.state_root = state_root
        self.tmp_dir = state_root / "tmp"
        self.config = config
        try:
            self.client = _build_s3_client(config)
        except (BotoCoreError, ValueError) as exc:
            raise ObjectStorageConfigurationError(
                "invalid_s3_configuration"
            ) from exc

    @classmethod
    def from_environment(cls, state_root: Path) -> "S3ObjectStore":
        return cls(state_root, S3ObjectStorageConfig.from_environment())

    def _validate_storage_key(self, storage_key: str) -> None:
        prefix = f"{self.config.prefix}/artifacts/"
        if (
            not storage_key.startswith(prefix)
            or "//" in storage_key
            or any(segment in {".", ".."} for segment in storage_key.split("/"))
        ):
            raise ObjectStorageConfigurationError("invalid_object_identity")

    def ensure_ready(self) -> None:
        self.tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.tmp_dir.chmod(0o700)
        try:
            self.client.list_objects_v2(
                Bucket=self.config.bucket,
                Prefix=self.config.prefix,
                MaxKeys=1,
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc

    def build_storage_key(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
        artifact_version_id: str,
        version_number: int,
        sha256: str,
    ) -> str:
        for value in (workspace_id, artifact_id, artifact_version_id):
            _validate_internal_id(value)
        _validate_sha256(sha256)
        if version_number < 1:
            raise ObjectStorageConfigurationError("invalid_object_identity")
        return (
            f"{self.config.prefix}/artifacts/{workspace_id}/{artifact_id}/"
            f"{artifact_version_id}/v{version_number:08d}-{sha256}.blob"
        )

    def _head(
        self,
        storage_key: str,
        *,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, str] = {
            "Bucket": self.config.bucket,
            "Key": storage_key,
        }
        if version_id is not None:
            arguments["VersionId"] = version_id
        try:
            return self.client.head_object(**arguments)
        except ClientError as exc:
            if _client_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectStorageMissingError("object_missing") from exc
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc
        except (BotoCoreError, OSError) as exc:
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc

    def put_file(
        self,
        source_path: Path,
        *,
        storage_key: str,
        size_bytes: int,
        sha256: str,
        content_md5: str,
        artifact_id: str,
        artifact_version_id: str,
    ) -> PutObjectReceipt:
        self._validate_storage_key(storage_key)
        _validate_sha256(sha256)
        _validate_internal_id(artifact_id)
        _validate_internal_id(artifact_version_id)
        metadata = {
            "kmfa-sha256": sha256,
            "kmfa-artifact-id": artifact_id,
            "kmfa-artifact-version-id": artifact_version_id,
            "kmfa-versioning": "immutable-key-v1",
        }
        try:
            with source_path.open("rb") as source:
                response = self.client.put_object(
                    Bucket=self.config.bucket,
                    Key=storage_key,
                    Body=source,
                    ContentLength=size_bytes,
                    ContentMD5=content_md5,
                    ContentType="application/octet-stream",
                    CacheControl="private, no-store",
                    ContentDisposition="attachment",
                    Metadata=metadata,
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            if _client_error_code(exc) in {
                "412",
                "ConditionalRequestConflict",
                "PreconditionFailed",
            }:
                raise ObjectStorageConflictError("immutable_object_exists") from exc
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc
        except (BotoCoreError, OSError) as exc:
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc

        head = self._head(storage_key)
        actual_metadata = head.get("Metadata", {})
        if (
            int(head.get("ContentLength", -1)) != size_bytes
            or actual_metadata.get("kmfa-sha256") != sha256
            or actual_metadata.get("kmfa-artifact-id") != artifact_id
            or actual_metadata.get("kmfa-artifact-version-id")
            != artifact_version_id
            or actual_metadata.get("kmfa-versioning") != "immutable-key-v1"
        ):
            raise ObjectStorageIntegrityError("object_integrity_failed")
        return PutObjectReceipt(
            storage_backend=self.storage_backend,
            storage_key=storage_key,
            etag=_etag(response.get("ETag") or head.get("ETag")),
            provider_version_id=(
                response.get("VersionId") or head.get("VersionId")
            ),
        )

    def _download_to_path(
        self,
        *,
        storage_key: str,
        target: Path,
    ) -> tuple[int, str]:
        try:
            response = self.client.get_object(
                Bucket=self.config.bucket,
                Key=storage_key,
            )
            body = response["Body"]
            digest = hashlib.sha256()
            size = 0
            try:
                descriptor = os.open(
                    target,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                with os.fdopen(descriptor, "wb") as output:
                    while True:
                        chunk = body.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        digest.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            finally:
                body.close()
            return size, digest.hexdigest()
        except ClientError as exc:
            _safe_unlink(target)
            if _client_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectStorageMissingError("object_missing") from exc
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc
        except (BotoCoreError, OSError, KeyError) as exc:
            _safe_unlink(target)
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc

    def materialize_verified(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
    ) -> MaterializedObject:
        self._validate_storage_key(storage_key)
        _validate_sha256(expected_sha256)
        self.tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.tmp_dir.chmod(0o700)
        target = self.tmp_dir / f"download-{secrets.token_urlsafe(24)}.part"
        size, sha256 = self._download_to_path(
            storage_key=storage_key,
            target=target,
        )
        if size != expected_size or sha256 != expected_sha256:
            _safe_unlink(target)
            raise ObjectStorageIntegrityError("object_integrity_failed")
        target.chmod(0o600)
        return MaterializedObject(path=target, temporary=True)

    def verify_existing(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
        artifact_id: str,
        artifact_version_id: str,
    ) -> PutObjectReceipt:
        """Deep-verify a conditional-write conflict or unknown timeout result."""

        self._validate_storage_key(storage_key)
        _validate_sha256(expected_sha256)
        _validate_internal_id(artifact_id)
        _validate_internal_id(artifact_version_id)
        head = self._head(storage_key)
        metadata = head.get("Metadata", {})
        if (
            int(head.get("ContentLength", -1)) != expected_size
            or metadata.get("kmfa-sha256") != expected_sha256
            or metadata.get("kmfa-artifact-id") != artifact_id
            or metadata.get("kmfa-artifact-version-id")
            != artifact_version_id
            or metadata.get("kmfa-versioning") != "immutable-key-v1"
        ):
            raise ObjectStorageIntegrityError("object_integrity_failed")
        materialized = self.materialize_verified(
            storage_key=storage_key,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        if materialized.temporary:
            _safe_unlink(materialized.path)
        return PutObjectReceipt(
            storage_backend=self.storage_backend,
            storage_key=storage_key,
            etag=_etag(head.get("ETag")),
            provider_version_id=head.get("VersionId"),
        )

    def inventory(self) -> list[InventoryObject]:
        """Return a deep, byte-hashed inventory for the configured private prefix."""

        items: list[InventoryObject] = []
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.config.bucket,
                Prefix=f"{self.config.prefix}/artifacts/",
            )
            for page in pages:
                for listed in page.get("Contents", []):
                    storage_key = str(listed["Key"])
                    self._validate_storage_key(storage_key)
                    head = self._head(storage_key)
                    target = self.tmp_dir / (
                        f"inventory-{secrets.token_urlsafe(24)}.part"
                    )
                    self.tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                    size, sha256 = self._download_to_path(
                        storage_key=storage_key,
                        target=target,
                    )
                    _safe_unlink(target)
                    metadata = head.get("Metadata", {})
                    items.append(
                        InventoryObject(
                            storage_key=storage_key,
                            size_bytes=size,
                            sha256=sha256,
                            metadata_sha256=metadata.get("kmfa-sha256"),
                            artifact_id=metadata.get("kmfa-artifact-id"),
                            artifact_version_id=metadata.get(
                                "kmfa-artifact-version-id"
                            ),
                            etag=_etag(head.get("ETag")),
                            provider_version_id=head.get("VersionId"),
                        )
                    )
        except ObjectStorageError:
            raise
        except (BotoCoreError, ClientError, OSError, KeyError) as exc:
            raise ObjectStorageUnavailableError("object_store_unavailable") from exc
        return sorted(items, key=lambda item: item.storage_key)

    def _provider_versions(
        self,
        *,
        prefix: str,
    ) -> list[tuple[str, str, bool]]:
        """List every native version and delete marker under one private prefix.

        A current-object listing cannot prove that a versioned target is empty:
        delete markers may hide historical bytes. Callers that authorize
        destructive deletion or isolated restore therefore require this exact
        provider inventory and fail closed when the API or permission is absent.
        """

        versions: list[tuple[str, str, bool]] = []
        try:
            paginator = self.client.get_paginator("list_object_versions")
            pages = paginator.paginate(
                Bucket=self.config.bucket,
                Prefix=prefix,
            )
            for page in pages:
                for field, delete_marker in (
                    ("Versions", False),
                    ("DeleteMarkers", True),
                ):
                    for item in page.get(field, []):
                        storage_key = str(item.get("Key", ""))
                        version_id = str(item.get("VersionId", ""))
                        if not storage_key or not version_id:
                            raise ObjectStorageUnavailableError(
                                "object_store_unavailable"
                            )
                        versions.append(
                            (storage_key, version_id, delete_marker)
                        )
        except ObjectStorageError:
            raise
        except ClientError as exc:
            if _client_error_code(exc) in {
                "MethodNotAllowed",
                "NotImplemented",
                "UnsupportedOperation",
                "501",
            }:
                raise ObjectStorageUnavailableError(
                    "object_version_inventory_unavailable"
                ) from exc
            raise ObjectStorageUnavailableError(
                "object_store_unavailable"
            ) from exc
        except (BotoCoreError, OSError, AttributeError, KeyError) as exc:
            raise ObjectStorageUnavailableError(
                "object_store_unavailable"
            ) from exc
        return versions

    def provider_version_count(self) -> int:
        """Count all current, historical and delete-marker versions in scope."""

        prefix = f"{self.config.prefix}/artifacts/"
        return len(self._provider_versions(prefix=prefix))

    def delete_all_versions(
        self,
        *,
        storage_key: str,
        expected_size: int,
        expected_sha256: str,
        artifact_id: str,
        artifact_version_id: str,
        missing_is_success: bool,
    ) -> int:
        """Delete every provider version of one immutable application key."""

        self._validate_storage_key(storage_key)
        _validate_sha256(expected_sha256)
        _validate_internal_id(artifact_id)
        _validate_internal_id(artifact_version_id)

        def validate_head(head: dict[str, Any]) -> None:
            metadata = head.get("Metadata", {})
            if (
                int(head.get("ContentLength", -1)) != expected_size
                or metadata.get("kmfa-sha256") != expected_sha256
                or metadata.get("kmfa-artifact-id") != artifact_id
                or metadata.get("kmfa-artifact-version-id")
                != artifact_version_id
            ):
                raise ObjectStorageIntegrityError("object_integrity_failed")

        def exact_provider_versions() -> list[tuple[str, bool]]:
            return [
                (version_id, delete_marker)
                for key, version_id, delete_marker in self._provider_versions(
                    prefix=storage_key
                )
                if key == storage_key
            ]

        current: dict[str, Any] | None
        try:
            current = self._head(storage_key)
        except ObjectStorageMissingError:
            current = None
        if current is not None:
            validate_head(current)

        versions = exact_provider_versions()

        if not versions:
            if current is None and missing_is_success:
                return 0
            if current is None:
                raise ObjectStorageMissingError("object_missing")
            # A version-capable provider returning an empty inventory for a
            # readable key cannot prove that all historical bytes are known.
            raise ObjectStorageUnavailableError("object_store_unavailable")

        for version_id, delete_marker in versions:
            if not delete_marker:
                validate_head(
                    self._head(
                        storage_key,
                        version_id=version_id,
                    )
                )

        deleted = 0
        try:
            for version_id, _ in versions:
                self.client.delete_object(
                    Bucket=self.config.bucket,
                    Key=storage_key,
                    VersionId=version_id,
                )
                deleted += 1
        except ObjectStorageError:
            raise
        except (BotoCoreError, ClientError, OSError) as exc:
            raise ObjectStorageUnavailableError(
                "object_store_unavailable"
            ) from exc

        remaining = exact_provider_versions()
        if remaining:
            raise ObjectStorageUnavailableError("object_store_unavailable")
        try:
            self._head(storage_key)
        except ObjectStorageMissingError:
            return deleted
        raise ObjectStorageUnavailableError("object_store_unavailable")


def configured_write_store(state_root: Path):
    mode = os.environ.get(
        "KMFA_ARTIFACT_STORAGE_MODE", LEGACY_FILESYSTEM_MODE
    ).strip()
    if mode == LEGACY_FILESYSTEM_MODE:
        return FilesystemObjectStore(state_root)
    if mode == S3_COMPATIBLE_MODE:
        return S3ObjectStore.from_environment(state_root)
    raise ObjectStorageConfigurationError("invalid_object_storage_mode")


def object_store_for_backend(state_root: Path, storage_backend: str):
    if storage_backend == LEGACY_STORAGE_BACKEND:
        return FilesystemObjectStore(state_root)
    if storage_backend == S3_STORAGE_BACKEND:
        return S3ObjectStore.from_environment(state_root)
    raise ObjectStorageConfigurationError("unknown_object_storage_backend")


def lifecycle_store_for_backend(state_root: Path, storage_backend: str):
    """Resolve the separately credentialed destructive lifecycle adapter."""

    if storage_backend == LEGACY_STORAGE_BACKEND:
        if os.environ.get(LEGACY_LIFECYCLE_DELETE_ENV, "").strip() != "1":
            raise ObjectStorageConfigurationError(
                "legacy_lifecycle_delete_not_allowed"
            )
        return FilesystemObjectStore(state_root)
    if storage_backend == S3_STORAGE_BACKEND:
        config = S3ObjectStorageConfig.from_environment(
            access_key_env="KMFA_S3_LIFECYCLE_ACCESS_KEY_ID",
            secret_key_env="KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY",
        )
        return S3ObjectStore(state_root, config)
    raise ObjectStorageConfigurationError("unknown_object_storage_backend")


def s3_dual_read_configured() -> bool:
    try:
        S3ObjectStorageConfig.from_environment()
    except ObjectStorageConfigurationError:
        return False
    return True


def content_md5_base64(digest: Any) -> str:
    return base64.b64encode(digest.digest()).decode("ascii")
