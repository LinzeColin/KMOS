"""Configuration for the isolated cloud runtime.

No ``KMFA_*`` DWS value is read as a fallback.  That prevents an apparently
working deployment from accidentally borrowing another skill's group, profile,
private database, or login state.
"""

from __future__ import annotations

import base64
import hashlib
import os
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from urllib.parse import urlsplit
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigError(ValueError):
    pass


ALLOWED_PRIVATE_REPOSITORIES = frozenset({
    "git@github.com:LinzeColin/Private-Database.git",
})

# GitHubProject rule 7 requires every new periodic R2 writer to remain below
# 40% of the public Standard free tier under a pessimistic 31-day month.  The
# guard keeps these values in one place so both configuration validation and
# its values-free receipt use identical arithmetic.
R2_FREE_TIER_CLASS_A_OPERATIONS = 1_000_000
R2_FREE_TIER_CLASS_B_OPERATIONS = 10_000_000
R2_FREE_TIER_STORAGE_BYTES = 10_000_000_000
R2_FREE_TIER_MAX_UTILIZATION_BPS = 4_000
R2_GUARD_MONTH_DAYS = 31
R2_POLLS_PER_DAY = 96
R2_MANIFEST_MAX_BYTES = 65_536


def _nonempty(env: Mapping[str, str], name: str, default: str = "") -> str:
    return str(env.get(name, default) or "").strip()


def _source_id_list(
    env: Mapping[str, str],
    name: str,
    *,
    fallback: str,
) -> tuple[str, ...]:
    """Read one bounded, explicit sender allowlist.

    The legacy one-sender value remains a valid deployment contract.  A
    configured list is an explicit allowlist for one already-configured group;
    it does not turn the collector into a group-member discovery scan.
    """

    raw = _nonempty(env, name)
    if not raw:
        return (fallback,) if fallback else ()
    if any(character.isspace() for character in raw) or ";" in raw:
        raise ConfigError("SOURCE_ID_LIST_INVALID")
    values = tuple(item for item in raw.split(",") if item)
    if not values or len(values) > 12 or len(set(values)) != len(values):
        raise ConfigError("SOURCE_ID_LIST_INVALID")
    return values


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = _nonempty(env, name, "1" if default else "0").lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name}_INVALID")


def _ocr_confidence_bps(env: Mapping[str, str]) -> int:
    raw = _nonempty(env, "DAILY_FUNDS_OCR_MIN_CONFIDENCE", "0.98")
    try:
        decimal = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ConfigError("DAILY_FUNDS_OCR_MIN_CONFIDENCE_INVALID") from exc
    if not decimal.is_finite() or decimal < Decimal("0.98") or decimal > Decimal("1"):
        raise ConfigError("DAILY_FUNDS_OCR_MIN_CONFIDENCE_INVALID")
    return int((decimal * 10_000).to_integral_value(rounding=ROUND_FLOOR))


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _nonempty(env, name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}_INVALID") from exc
    if value <= 0:
        raise ConfigError(f"{name}_INVALID")
    return value


def r2_worst_case_monthly_usage(
    *,
    max_new_objects_per_poll: int,
    max_new_bytes_per_poll: int,
) -> tuple[int, int, int]:
    """Return Class-A, Class-B and storage bounds for the scheduled slice.

    Every new object is pessimistically assumed to require a preflight GET,
    PUT, HEAD and byte-readback.  The normal publication then verifies the
    manifest/object set once more, while the daily cold-backup job verifies
    the most recent set.  The bound deliberately excludes any deduction for
    hash reuse, so a valid receipt remains safe if every 15-minute cycle is
    entirely new material.
    """

    if (
        isinstance(max_new_objects_per_poll, bool)
        or isinstance(max_new_bytes_per_poll, bool)
        or not isinstance(max_new_objects_per_poll, int)
        or not isinstance(max_new_bytes_per_poll, int)
        or max_new_objects_per_poll <= 0
        or max_new_bytes_per_poll <= 0
    ):
        raise ConfigError("R2_FREE_TIER_BUDGET_INVALID")
    objects_per_cycle = max_new_objects_per_poll + 1  # plus one manifest
    poll_cycles = R2_GUARD_MONTH_DAYS * R2_POLLS_PER_DAY
    class_a = objects_per_cycle * poll_cycles
    class_b = objects_per_cycle * ((4 * poll_cycles) + R2_GUARD_MONTH_DAYS)
    storage = (max_new_bytes_per_poll + R2_MANIFEST_MAX_BYTES) * poll_cycles
    return class_a, class_b, storage


def r2_worst_case_is_within_free_tier(
    *,
    max_new_objects_per_poll: int,
    max_new_bytes_per_poll: int,
) -> bool:
    class_a, class_b, storage = r2_worst_case_monthly_usage(
        max_new_objects_per_poll=max_new_objects_per_poll,
        max_new_bytes_per_poll=max_new_bytes_per_poll,
    )
    return (
        class_a * 10_000 < R2_FREE_TIER_CLASS_A_OPERATIONS * R2_FREE_TIER_MAX_UTILIZATION_BPS
        and class_b * 10_000 < R2_FREE_TIER_CLASS_B_OPERATIONS * R2_FREE_TIER_MAX_UTILIZATION_BPS
        and storage * 10_000 < R2_FREE_TIER_STORAGE_BYTES * R2_FREE_TIER_MAX_UTILIZATION_BPS
    )


@dataclass(frozen=True)
class DailyFundsConfig:
    state_dir: Path
    publication_dir: Path
    control_dir: Path
    dws_config_dir: Path
    dws_keyring_dir: Path
    dws_bin: str
    private_repo: str
    private_branch: str
    git_ssh_key_b64: str
    group_id: str
    sender_id: str
    sender_ids: tuple[str, ...]
    dws_client_id: str
    dws_auth_bundle_b64: str
    cf_api_token: str
    cf_account_id: str
    d1_database_id: str
    restore_drill_d1_database_id: str
    r2_endpoint_url: str
    r2_bucket: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_max_new_objects_per_poll: int
    r2_max_new_bytes_per_poll: int
    oci_endpoint_url: str
    oci_bucket: str
    oci_access_key_id: str
    oci_secret_access_key: str
    oci_region: str
    oci_par_url: str
    ocr_enabled: bool
    ocr_min_confidence_bps: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DailyFundsConfig":
        source = os.environ if env is None else env
        sender_id = _nonempty(source, "DAILY_FUNDS_SENDER_ID")
        return cls(
            state_dir=Path(_nonempty(source, "DAILY_FUNDS_STATE_DIR", "/var/lib/kmfa/daily-funds-state")),
            publication_dir=Path(_nonempty(source, "DAILY_FUNDS_PUBLICATION_DIR", "/var/lib/kmfa/daily-funds-publication")),
            control_dir=Path(_nonempty(source, "DAILY_FUNDS_CONTROL_DIR", "/var/lib/kmfa/daily-funds-control")),
            dws_config_dir=Path(_nonempty(source, "DAILY_FUNDS_DWS_CONFIG_DIR", "/var/lib/kmfa/daily-funds-dws/config")),
            dws_keyring_dir=Path(_nonempty(source, "DAILY_FUNDS_DWS_KEYRING_DIR", "/var/lib/kmfa/daily-funds-dws/keyring")),
            dws_bin=_nonempty(source, "DAILY_FUNDS_DWS_BIN", "dws"),
            private_repo=_nonempty(source, "DAILY_FUNDS_PRIVATE_REPO", "git@github.com:LinzeColin/Private-Database.git"),
            private_branch=_nonempty(source, "DAILY_FUNDS_PRIVATE_BRANCH", "main"),
            git_ssh_key_b64=_nonempty(source, "DAILY_FUNDS_GIT_SSH_KEY_B64"),
            group_id=_nonempty(source, "DAILY_FUNDS_GROUP_ID"),
            sender_id=sender_id,
            sender_ids=_source_id_list(
                source,
                "DAILY_FUNDS_SENDER_IDS",
                fallback=sender_id,
            ),
            dws_client_id=_nonempty(source, "DAILY_FUNDS_DWS_CLIENT_ID"),
            dws_auth_bundle_b64=_nonempty(source, "DAILY_FUNDS_DWS_AUTH_BUNDLE_B64"),
            cf_api_token=_nonempty(source, "DAILY_FUNDS_CLOUDFLARE_API_TOKEN"),
            cf_account_id=_nonempty(source, "DAILY_FUNDS_CF_ACCOUNT_ID"),
            d1_database_id=_nonempty(source, "DAILY_FUNDS_D1_DATABASE_ID"),
            restore_drill_d1_database_id=_nonempty(source, "DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID"),
            r2_endpoint_url=_nonempty(source, "DAILY_FUNDS_R2_ENDPOINT_URL"),
            r2_bucket=_nonempty(source, "DAILY_FUNDS_R2_BUCKET"),
            r2_access_key_id=_nonempty(source, "DAILY_FUNDS_R2_ACCESS_KEY_ID"),
            r2_secret_access_key=_nonempty(source, "DAILY_FUNDS_R2_SECRET_ACCESS_KEY"),
            r2_max_new_objects_per_poll=_positive_int(source, "DAILY_FUNDS_R2_MAX_NEW_OBJECTS_PER_POLL", 100),
            r2_max_new_bytes_per_poll=_positive_int(source, "DAILY_FUNDS_R2_MAX_NEW_BYTES_PER_POLL", 1_000_000),
            oci_endpoint_url=_nonempty(source, "DAILY_FUNDS_OCI_ENDPOINT_URL"),
            oci_bucket=_nonempty(source, "DAILY_FUNDS_OCI_BUCKET"),
            oci_access_key_id=_nonempty(source, "DAILY_FUNDS_OCI_ACCESS_KEY_ID"),
            oci_secret_access_key=_nonempty(source, "DAILY_FUNDS_OCI_SECRET_ACCESS_KEY"),
            oci_region=_nonempty(source, "DAILY_FUNDS_OCI_REGION", "ap-chuncheon-1"),
            oci_par_url=_nonempty(source, "DAILY_FUNDS_OCI_PAR_URL"),
            ocr_enabled=_flag(source, "DAILY_FUNDS_OCR_ENABLED", True),
            ocr_min_confidence_bps=_ocr_confidence_bps(source),
        )

    def missing(self, *, include_storage: bool = True) -> tuple[str, ...]:
        required = {
            "DAILY_FUNDS_GROUP_ID": self.group_id,
            "DAILY_FUNDS_SENDER_ID": self.sender_id,
            "DAILY_FUNDS_GIT_SSH_KEY_B64": self.git_ssh_key_b64,
        }
        if include_storage:
            required |= {
                "DAILY_FUNDS_CLOUDFLARE_API_TOKEN": self.cf_api_token,
                "DAILY_FUNDS_CF_ACCOUNT_ID": self.cf_account_id,
                "DAILY_FUNDS_D1_DATABASE_ID": self.d1_database_id,
                "DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID": self.restore_drill_d1_database_id,
                "DAILY_FUNDS_R2_ENDPOINT_URL": self.r2_endpoint_url,
                "DAILY_FUNDS_R2_BUCKET": self.r2_bucket,
                "DAILY_FUNDS_R2_ACCESS_KEY_ID": self.r2_access_key_id,
                "DAILY_FUNDS_R2_SECRET_ACCESS_KEY": self.r2_secret_access_key,
            }
            # OCI cold backup has two mutually exclusive credential modes.
            # The production path is one bucket-scoped PAR URL; legacy
            # S3-compatible HMAC values remain accepted for an explicit
            # migration/recovery deployment only.
            if not self.oci_par_url:
                required |= {
                    "DAILY_FUNDS_OCI_ENDPOINT_URL": self.oci_endpoint_url,
                    "DAILY_FUNDS_OCI_BUCKET": self.oci_bucket,
                    "DAILY_FUNDS_OCI_ACCESS_KEY_ID": self.oci_access_key_id,
                    "DAILY_FUNDS_OCI_SECRET_ACCESS_KEY": self.oci_secret_access_key,
                }
        return tuple(sorted(name for name, value in required.items() if not value))

    def _validate_runtime_paths(self) -> None:
        for path in (self.state_dir, self.publication_dir, self.control_dir, self.dws_config_dir, self.dws_keyring_dir):
            if path.is_absolute() is False:
                raise ConfigError("RUNTIME_PATH_MUST_BE_ABSOLUTE")

    def validate_dws_bootstrap(self) -> None:
        """Validate only the cloud-side prerequisites for one explicit login.

        A portable bundle is deliberately not required here: a fresh cloud
        volume must be able to establish its own dedicated DWS profile without
        copying a local profile or passing a host-exported credential through
        an environment variable.
        """

        self._validate_runtime_paths()

    def _validate_exact_dws_source(self) -> None:
        """Validate only the independent exact-group DWS read contract.

        The pending-payment snapshot reads no private Git or object storage.
        Keeping this source validation separate prevents an unrelated archive
        or publication credential fault from withholding an otherwise current
        DWS operational view.
        """

        required = {
            "DAILY_FUNDS_GROUP_ID": self.group_id,
            "DAILY_FUNDS_SENDER_ID": self.sender_id,
        }
        missing = tuple(sorted(name for name, value in required.items() if not value))
        if missing:
            raise ConfigError("CONFIG_INVALID:" + ",".join(missing))
        # The source gate accepts one opaque group ID and a small, static
        # sender allowlist.  Group membership is never used as a runtime
        # selector: every ID is supplied through the deployment configuration
        # and rechecked again for each returned message.
        if any(char.isspace() for char in self.group_id) or "," in self.group_id or ";" in self.group_id:
            raise ConfigError("SOURCE_ID_NOT_UNIQUE")
        if (
            not self.sender_ids
            or len(self.sender_ids) > 12
            or self.sender_id not in self.sender_ids
            or len(set(self.sender_ids)) != len(self.sender_ids)
        ):
            raise ConfigError("SOURCE_ID_LIST_INVALID")
        for source_id in self.sender_ids:
            if not source_id or any(char.isspace() for char in source_id) or "," in source_id or ";" in source_id:
                raise ConfigError("SOURCE_ID_LIST_INVALID")
        # A bundle is an optional cloud-recovery import.  When configured, it
        # must still be a bounded base64 blob before any DWS invocation.
        if self.dws_auth_bundle_b64:
            try:
                auth_bundle = base64.b64decode(self.dws_auth_bundle_b64, validate=True)
            except Exception as exc:
                raise ConfigError("DWS_AUTH_BUNDLE_BASE64_INVALID") from exc
            if not auth_bundle or len(auth_bundle) > 8 * 1024 * 1024:
                raise ConfigError("DWS_AUTH_BUNDLE_FORMAT_INVALID")
        self._validate_runtime_paths()

    def validate_live_payment_request_source(self) -> None:
        """Validate the source-only contract for the public pending-payment view."""

        self._validate_exact_dws_source()

    def validate(self, *, include_storage: bool = True) -> None:
        missing = self.missing(include_storage=include_storage)
        if missing:
            raise ConfigError("CONFIG_INVALID:" + ",".join(missing))
        if self.private_branch != "main":
            raise ConfigError("PRIVATE_BRANCH_MUST_BE_MAIN")
        if self.private_repo not in ALLOWED_PRIVATE_REPOSITORIES:
            raise ConfigError("PRIVATE_REPOSITORY_NOT_ALLOWED")
        if isinstance(self.ocr_enabled, bool) is False:
            raise ConfigError("DAILY_FUNDS_OCR_ENABLED_INVALID")
        if (
            isinstance(self.ocr_min_confidence_bps, bool)
            or not isinstance(self.ocr_min_confidence_bps, int)
            or self.ocr_min_confidence_bps < 9_800
            or self.ocr_min_confidence_bps > 10_000
        ):
            raise ConfigError("DAILY_FUNDS_OCR_MIN_CONFIDENCE_INVALID")
        if include_storage and self.restore_drill_d1_database_id == self.d1_database_id:
            raise ConfigError("RESTORE_DRILL_D1_MUST_DIFFER")
        if not r2_worst_case_is_within_free_tier(
            max_new_objects_per_poll=self.r2_max_new_objects_per_poll,
            max_new_bytes_per_poll=self.r2_max_new_bytes_per_poll,
        ):
            raise ConfigError("R2_FREE_TIER_BUDGET_EXCEEDED")
        legacy_oci_values = (
            self.oci_endpoint_url,
            self.oci_bucket,
            self.oci_access_key_id,
            self.oci_secret_access_key,
        )
        if self.oci_par_url:
            if any(legacy_oci_values):
                raise ConfigError("OCI_CREDENTIAL_MODE_AMBIGUOUS")
            parsed_par = urlsplit(self.oci_par_url)
            path = parsed_par.path
            if (
                parsed_par.scheme != "https"
                or not parsed_par.netloc
                or parsed_par.username is not None
                or parsed_par.password is not None
                or parsed_par.query
                or parsed_par.fragment
                or not path.endswith("/o/")
                or not all(marker in path for marker in ("/p/", "/n/", "/b/", "/o/"))
            ):
                raise ConfigError("OCI_PAR_URL_INVALID")
        try:
            key = base64.b64decode(self.git_ssh_key_b64, validate=True)
        except Exception as exc:
            raise ConfigError("GIT_SSH_KEY_BASE64_INVALID") from exc
        if not key.startswith(b"-----BEGIN"):
            raise ConfigError("GIT_SSH_KEY_FORMAT_INVALID")
        self._validate_exact_dws_source()

    def redacted_fingerprint(self) -> str:
        """Evidence-only fingerprint; never returns values or credentials."""

        fields = (
            self.group_id,
            self.sender_id,
            str(len(self.sender_ids)),
            "\x1e".join(self.sender_ids),
            self.dws_client_id,
            hashlib.sha256(self.dws_auth_bundle_b64.encode("utf-8")).hexdigest(),
            self.cf_account_id,
            self.d1_database_id,
            self.restore_drill_d1_database_id,
            self.r2_bucket,
            str(self.r2_max_new_objects_per_poll),
            str(self.r2_max_new_bytes_per_poll),
            self.oci_bucket,
            hashlib.sha256(self.oci_par_url.encode("utf-8")).hexdigest(),
            "OCR_ENABLED" if self.ocr_enabled else "OCR_DISABLED",
            str(self.ocr_min_confidence_bps),
        )
        return hashlib.sha256("\x1f".join(fields).encode("utf-8")).hexdigest()
