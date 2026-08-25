#!/usr/bin/env python3
"""Manage only ephemeral files used by the fixed daily-funds Access bridge.

Provider responses may contain credentials and application identifiers.  This
tool never prints any input field or exception detail.  It either writes a
mode-0600 runner file or emits the finite probe receipt used by Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.access_bridge import (  # noqa: E402
    AccessBridgeInputError,
    capture_policy,
    capture_service_token,
    capture_service_token_id,
    owned_bridge_resource_ids,
    policy_payload,
    probe_poll_state,
    probe_start_poll_state,
    recovery_poll_state,
    recovery_start_poll_state,
    resolve_bridge_target,
    service_token_payload,
    summarize_recovery_start_response,
    summarize_recovery_response,
    summarize_probe_start_response,
    summarize_probe_response,
    validate_success_response,
    write_private_json,
)


def _private_output(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Path:
    target = Path(args.output)
    if not target.name or target.is_symlink():
        parser.error("private output path required")
    return target


def _write_shell_material(path: Path, values: dict[str, str]) -> None:
    # Values originate from strict parser functions and are shell-quoted once
    # here.  The workflow can source the mode-0600 file without turning a
    # provider response into shell syntax.
    allowed_keys = {
        "CF_ACCESS_APP_ID", "PROBE_ORIGIN", "CF_ACCESS_CLIENT_ID",
        "CF_ACCESS_CLIENT_SECRET", "CF_ACCESS_SERVICE_TOKEN_ID", "CF_ACCESS_POLICY_ID",
    }
    if (
        not values
        or any(
            not isinstance(key, str)
            or key not in allowed_keys
            or not isinstance(value, str)
            or not value
            or len(value) > 256
            or any(character in value for character in "\x00\r\n")
            for key, value in values.items()
        )
    ):
        raise AccessBridgeInputError("runner material invalid")
    lines = [f"{key}={shlex.quote(value)}" for key, value in sorted(values.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_owned_resource_material(path: Path, values: dict[str, tuple[str, ...]]) -> None:
    """Write only validated opaque IDs for a shell-only cleanup loop.

    Empty values are intentional: they mean the final provider read saw no
    resource for this exact run tag.  The workflow never prints this file.
    """

    expected = {"service_token_ids", "policy_ids"}
    if set(values) != expected:
        raise AccessBridgeInputError("owned resource material invalid")
    rendered: dict[str, str] = {}
    for source_key, target_key in (
        ("service_token_ids", "CF_ACCESS_OWNED_SERVICE_TOKEN_IDS"),
        ("policy_ids", "CF_ACCESS_OWNED_POLICY_IDS"),
    ):
        identifiers = values[source_key]
        if (
            not isinstance(identifiers, tuple)
            or any(
                not isinstance(identifier, str)
                or len(identifier) != 36
                or any(character not in "0123456789abcdef-" for character in identifier)
                for identifier in identifiers
            )
        ):
            raise AccessBridgeInputError("owned resource material invalid")
        rendered[target_key] = " ".join(identifiers)
    lines = [f"{key}={shlex.quote(value)}" for key, value in sorted(rendered.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-target")
    resolve.add_argument("--coolify-env", required=True)
    resolve.add_argument("--access-apps", required=True)
    resolve.add_argument("--output", required=True)

    service_payload = subparsers.add_parser("write-service-token-payload")
    service_payload.add_argument("--run-tag", required=True)
    service_payload.add_argument("--output", required=True)

    capture_service = subparsers.add_parser("capture-service-token")
    capture_service.add_argument("--response", required=True)
    capture_service.add_argument("--output", required=True)

    capture_service_id = subparsers.add_parser("capture-service-token-id")
    capture_service_id.add_argument("--response", required=True)
    capture_service_id.add_argument("--output", required=True)

    policy = subparsers.add_parser("write-policy-payload")
    policy.add_argument("--service-material", required=True)
    policy.add_argument("--run-tag", required=True)
    policy.add_argument("--output", required=True)

    capture_policy_parser = subparsers.add_parser("capture-policy")
    capture_policy_parser.add_argument("--response", required=True)
    capture_policy_parser.add_argument("--output", required=True)

    summary = subparsers.add_parser("summarize-probe")
    summary.add_argument("--response", required=True)
    summary.add_argument("--headers", required=True)
    summary.add_argument("--http-status", required=True)
    summary.add_argument("--curl-exit", required=True)
    summary.add_argument("--output")

    start_summary = subparsers.add_parser("summarize-probe-start")
    start_summary.add_argument("--response", required=True)
    start_summary.add_argument("--headers", required=True)
    start_summary.add_argument("--http-status", required=True)
    start_summary.add_argument("--curl-exit", required=True)
    start_summary.add_argument("--output")

    success = subparsers.add_parser("validate-success")
    success.add_argument("--response", required=True)

    poll = subparsers.add_parser("probe-poll-state")
    poll.add_argument("--receipt", required=True)

    start_poll = subparsers.add_parser("probe-start-poll-state")
    start_poll.add_argument("--receipt", required=True)

    recovery_summary = subparsers.add_parser("summarize-recovery")
    recovery_summary.add_argument("--response", required=True)
    recovery_summary.add_argument("--headers", required=True)
    recovery_summary.add_argument("--http-status", required=True)
    recovery_summary.add_argument("--curl-exit", required=True)
    recovery_summary.add_argument("--output")

    recovery_start_summary = subparsers.add_parser("summarize-recovery-start")
    recovery_start_summary.add_argument("--response", required=True)
    recovery_start_summary.add_argument("--headers", required=True)
    recovery_start_summary.add_argument("--http-status", required=True)
    recovery_start_summary.add_argument("--curl-exit", required=True)
    recovery_start_summary.add_argument("--output")

    recovery_poll = subparsers.add_parser("recovery-poll-state")
    recovery_poll.add_argument("--receipt", required=True)

    recovery_start_poll = subparsers.add_parser("recovery-start-poll-state")
    recovery_start_poll.add_argument("--receipt", required=True)

    owned = subparsers.add_parser("write-owned-resource-env")
    owned.add_argument("--service-tokens", required=True)
    owned.add_argument("--policies", required=True)
    owned.add_argument("--run-tag", required=True)
    owned.add_argument("--output", required=True)

    owned_state = subparsers.add_parser("owned-resource-state")
    owned_state.add_argument("--service-tokens", required=True)
    owned_state.add_argument("--policies", required=True)
    owned_state.add_argument("--run-tag", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "resolve-target":
            target = resolve_bridge_target(args.coolify_env, args.access_apps)
            _write_shell_material(_private_output(parser, args), {
                "CF_ACCESS_APP_ID": target["app_id"],
                "PROBE_ORIGIN": target["origin"],
            })
        elif args.command == "write-service-token-payload":
            write_private_json(_private_output(parser, args), service_token_payload(args.run_tag))
        elif args.command == "capture-service-token":
            material = capture_service_token(args.response)
            _write_shell_material(_private_output(parser, args), {
                "CF_ACCESS_CLIENT_ID": material["client_id"],
                "CF_ACCESS_CLIENT_SECRET": material["client_secret"],
                "CF_ACCESS_SERVICE_TOKEN_ID": material["service_token_id"],
            })
        elif args.command == "capture-service-token-id":
            material = capture_service_token_id(args.response)
            _write_shell_material(_private_output(parser, args), {
                "CF_ACCESS_SERVICE_TOKEN_ID": material["service_token_id"],
            })
        elif args.command == "write-policy-payload":
            material = _read_shell_material(args.service_material)
            write_private_json(
                _private_output(parser, args),
                policy_payload(material["CF_ACCESS_SERVICE_TOKEN_ID"], args.run_tag),
            )
        elif args.command == "capture-policy":
            material = capture_policy(args.response)
            _write_shell_material(_private_output(parser, args), {"CF_ACCESS_POLICY_ID": material["policy_id"]})
        elif args.command == "summarize-probe":
            receipt = summarize_probe_response(
                args.response,
                response_headers_path=args.headers,
                http_status=args.http_status,
                curl_exit=args.curl_exit,
            )
            if args.output:
                write_private_json(_private_output(parser, args), receipt)
            else:
                print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        elif args.command == "summarize-probe-start":
            receipt = summarize_probe_start_response(
                args.response,
                response_headers_path=args.headers,
                http_status=args.http_status,
                curl_exit=args.curl_exit,
            )
            if args.output:
                write_private_json(_private_output(parser, args), receipt)
            else:
                print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        elif args.command == "validate-success":
            return 0 if validate_success_response(args.response) else 1
        elif args.command == "probe-poll-state":
            print(probe_poll_state(args.receipt))
        elif args.command == "probe-start-poll-state":
            print(probe_start_poll_state(args.receipt))
        elif args.command == "summarize-recovery":
            receipt = summarize_recovery_response(
                args.response,
                response_headers_path=args.headers,
                http_status=args.http_status,
                curl_exit=args.curl_exit,
            )
            if args.output:
                write_private_json(_private_output(parser, args), receipt)
            else:
                print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        elif args.command == "summarize-recovery-start":
            receipt = summarize_recovery_start_response(
                args.response,
                response_headers_path=args.headers,
                http_status=args.http_status,
                curl_exit=args.curl_exit,
            )
            if args.output:
                write_private_json(_private_output(parser, args), receipt)
            else:
                print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        elif args.command == "recovery-poll-state":
            print(recovery_poll_state(args.receipt))
        elif args.command == "recovery-start-poll-state":
            print(recovery_start_poll_state(args.receipt))
        elif args.command == "write-owned-resource-env":
            _write_owned_resource_material(
                _private_output(parser, args),
                owned_bridge_resource_ids(
                    args.service_tokens,
                    args.policies,
                    args.run_tag,
                ),
            )
        elif args.command == "owned-resource-state":
            resources = owned_bridge_resource_ids(
                args.service_tokens,
                args.policies,
                args.run_tag,
            )
            print(
                "ABSENT"
                if not resources["service_token_ids"] and not resources["policy_ids"]
                else "PRESENT"
            )
        else:  # pragma: no cover - argparse owns this branch.
            parser.error("unsupported command")
    except (AccessBridgeInputError, KeyError, OSError, ValueError):
        print("daily_funds_access_bridge_input_invalid", file=sys.stderr)
        return 2
    return 0


def _read_shell_material(path: str) -> dict[str, str]:
    """Read only the exact shell file generated by this module itself."""

    try:
        target = Path(path)
        if target.is_symlink() or target.stat().st_mode & 0o077:
            raise AccessBridgeInputError("service material invalid")
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AccessBridgeInputError("service material unavailable") from exc
    result: dict[str, str] = {}
    allowed = {"CF_ACCESS_SERVICE_TOKEN_ID", "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "CF_ACCESS_POLICY_ID"}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator != "=" or key not in allowed:
            raise AccessBridgeInputError("service material invalid")
        try:
            parts = shlex.split(value, posix=True)
        except ValueError as exc:
            raise AccessBridgeInputError("service material invalid") from exc
        if len(parts) != 1:
            raise AccessBridgeInputError("service material invalid")
        candidate = parts[0]
        if not candidate or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for character in candidate):
            raise AccessBridgeInputError("service material invalid")
        result[key] = candidate
    if set(result) != {"CF_ACCESS_SERVICE_TOKEN_ID", "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET"}:
        raise AccessBridgeInputError("service material invalid")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
