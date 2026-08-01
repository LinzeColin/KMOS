"""Configuration for the isolated cloud runtime.

No ``KMFA_*`` DWS value is read as a fallback.  That prevents an apparently
working deployment from accidentally borrowing another skill's group, profile,
private database, or login state.
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigError(ValueError):
    pass


ALLOWED_PRIVATE_REPOSITORIES = frozenset({
    "git@github.com:LinzeColin/Private-Database.git",
})


def _nonempty(env: Mapping[str, str], name: str, default: str = "") -> str:
    return str(env.get(name, default) or "").strip()


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
    oci_endpoint_url: str
    oci_bucket: str
    oci_access_key_id: str
    oci_secret_access_key: str
    oci_region: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DailyFundsConfig":
        source = os.environ if env is None else env
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
            sender_id=_nonempty(source, "DAILY_FUNDS_SENDER_ID"),
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
            oci_endpoint_url=_nonempty(source, "DAILY_FUNDS_OCI_ENDPOINT_URL"),
            oci_bucket=_nonempty(source, "DAILY_FUNDS_OCI_BUCKET"),
            oci_access_key_id=_nonempty(source, "DAILY_FUNDS_OCI_ACCESS_KEY_ID"),
            oci_secret_access_key=_nonempty(source, "DAILY_FUNDS_OCI_SECRET_ACCESS_KEY"),
            oci_region=_nonempty(source, "DAILY_FUNDS_OCI_REGION", "ap-chuncheon-1"),
        )

    def missing(self, *, include_storage: bool = True) -> tuple[str, ...]:
        required = {
            "DAILY_FUNDS_GROUP_ID": self.group_id,
            "DAILY_FUNDS_SENDER_ID": self.sender_id,
            "DAILY_FUNDS_DWS_CLIENT_ID": self.dws_client_id,
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

        if not self.dws_client_id:
            raise ConfigError("CONFIG_INVALID:DAILY_FUNDS_DWS_CLIENT_ID")
        self._validate_runtime_paths()

    def validate(self, *, include_storage: bool = True) -> None:
        missing = self.missing(include_storage=include_storage)
        if missing:
            raise ConfigError("CONFIG_INVALID:" + ",".join(missing))
        if self.private_branch != "main":
            raise ConfigError("PRIVATE_BRANCH_MUST_BE_MAIN")
        if self.private_repo not in ALLOWED_PRIVATE_REPOSITORIES:
            raise ConfigError("PRIVATE_REPOSITORY_NOT_ALLOWED")
        if include_storage and self.restore_drill_d1_database_id == self.d1_database_id:
            raise ConfigError("RESTORE_DRILL_D1_MUST_DIFFER")
        # The source gate accepts one opaque group ID and one opaque sender ID
        # only.  A comma/newline separated value is a common accidental way to
        # turn a single-source contract into a multi-source scan; reject it
        # rather than trying to interpret it.
        for source_id in (self.group_id, self.sender_id):
            if any(char.isspace() for char in source_id) or "," in source_id or ";" in source_id:
                raise ConfigError("SOURCE_ID_NOT_UNIQUE")
        try:
            key = base64.b64decode(self.git_ssh_key_b64, validate=True)
        except Exception as exc:
            raise ConfigError("GIT_SSH_KEY_BASE64_INVALID") from exc
        if not key.startswith(b"-----BEGIN"):
            raise ConfigError("GIT_SSH_KEY_FORMAT_INVALID")
        # A bundle is an optional cloud-recovery import.  The preferred path
        # is a first-time device login performed inside this service's own
        # cloud volume; making an exported bundle mandatory would reintroduce
        # a hidden workstation dependency.
        if self.dws_auth_bundle_b64:
            try:
                auth_bundle = base64.b64decode(self.dws_auth_bundle_b64, validate=True)
            except Exception as exc:
                raise ConfigError("DWS_AUTH_BUNDLE_BASE64_INVALID") from exc
            if not auth_bundle or len(auth_bundle) > 8 * 1024 * 1024:
                raise ConfigError("DWS_AUTH_BUNDLE_FORMAT_INVALID")
        self._validate_runtime_paths()

    def redacted_fingerprint(self) -> str:
        """Evidence-only fingerprint; never returns values or credentials."""

        fields = (
            self.group_id,
            self.sender_id,
            self.dws_client_id,
            hashlib.sha256(self.dws_auth_bundle_b64.encode("utf-8")).hexdigest(),
            self.cf_account_id,
            self.d1_database_id,
            self.restore_drill_d1_database_id,
            self.r2_bucket,
            self.oci_bucket,
        )
        return hashlib.sha256("\x1f".join(fields).encode("utf-8")).hexdigest()
