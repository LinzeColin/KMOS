"""Deterministic DB/object inventory reconciliation for S05/P5.2."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from .object_storage import InventoryObject, S3_STORAGE_BACKEND, S3ObjectStore
from .structured_repository import StructuredRepository
from .structured_store import StructuredStoreConnection

REPAIR_STATES = {
    "missing_object": "restore_expected_object_or_mark_missing",
    "orphan_object": "quarantine_unindexed_object",
    "object_metadata_mismatch": "block_read_and_restore_expected_object",
    "duplicate_index_key": "block_duplicate_index_and_repair_db",
}


def _opaque_ref(storage_key: str) -> str:
    return hashlib.sha256(storage_key.encode("utf-8")).hexdigest()[:20]


def _anomaly(
    anomaly_type: str,
    storage_key: str,
    *,
    mismatched_fields: Iterable[str] = (),
    affected_records: int = 1,
) -> dict[str, Any]:
    return {
        "type": anomaly_type,
        "object_ref": _opaque_ref(storage_key),
        "repair_state": REPAIR_STATES[anomaly_type],
        "mismatched_fields": sorted(set(mismatched_fields)),
        "affected_records": affected_records,
    }


def reconcile_object_inventory(
    index_rows: Iterable[Mapping[str, Any]],
    inventory: Iterable[InventoryObject],
) -> dict[str, Any]:
    rows = [dict(row) for row in index_rows]
    objects = list(inventory)
    rows_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_key[str(row["storage_key"])].append(row)
    objects_by_key = {item.storage_key: item for item in objects}

    anomalies: list[dict[str, Any]] = []
    consistent = 0
    for storage_key, key_rows in sorted(rows_by_key.items()):
        if len(key_rows) > 1:
            anomalies.append(
                _anomaly(
                    "duplicate_index_key",
                    storage_key,
                    affected_records=len(key_rows),
                )
            )
            continue
        row = key_rows[0]
        item = objects_by_key.get(storage_key)
        if item is None:
            anomalies.append(_anomaly("missing_object", storage_key))
            continue
        mismatches: list[str] = []
        if int(row["size_bytes"]) != item.size_bytes:
            mismatches.append("size_bytes")
        if str(row["sha256"]) != item.sha256:
            mismatches.append("sha256")
        if item.metadata_sha256 != str(row["sha256"]):
            mismatches.append("metadata_sha256")
        if item.artifact_id != str(row["artifact_id"]):
            mismatches.append("artifact_id")
        if item.artifact_version_id != str(row["artifact_version_id"]):
            mismatches.append("artifact_version_id")
        if mismatches:
            anomalies.append(
                _anomaly(
                    "object_metadata_mismatch",
                    storage_key,
                    mismatched_fields=mismatches,
                )
            )
        else:
            consistent += 1

    for storage_key in sorted(set(objects_by_key) - set(rows_by_key)):
        anomalies.append(_anomaly("orphan_object", storage_key))

    anomalies.sort(key=lambda item: (item["type"], item["object_ref"]))
    anomaly_counts = Counter(item["type"] for item in anomalies)
    indexed_count = len(rows)
    consistency_rate = 1.0 if indexed_count == 0 else consistent / indexed_count
    unexplained = sum(
        count
        for anomaly_type, count in anomaly_counts.items()
        if anomaly_type not in REPAIR_STATES
    )
    return {
        "schema_version": "kmfa.s05.p52.object-reconciliation.v1",
        "storage_backend": S3_STORAGE_BACKEND,
        "indexed_objects": indexed_count,
        "inventory_objects": len(objects),
        "consistent_objects": consistent,
        "normal_object_consistency_rate": consistency_rate,
        "anomaly_count": len(anomalies),
        "anomaly_counts": dict(sorted(anomaly_counts.items())),
        "classified_anomalies": len(anomalies) - unexplained,
        "unexplained_anomalies": unexplained,
        "repair_states_deterministic": all(
            item["repair_state"] == REPAIR_STATES[item["type"]]
            for item in anomalies
        ),
        "pass_gate": consistency_rate == 1.0 and not anomalies,
        "anomalies": anomalies,
    }


def reconcile_s3_store(
    connection: StructuredStoreConnection,
    store: S3ObjectStore,
) -> dict[str, Any]:
    rows = StructuredRepository(connection).artifact_object_index(
        storage_backend=S3_STORAGE_BACKEND
    )
    return reconcile_object_inventory(rows, store.inventory())
