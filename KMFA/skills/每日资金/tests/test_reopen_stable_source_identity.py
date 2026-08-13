from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest

from daily_funds.ingestion import (
    DownloadedAttachment,
    IngestionError,
    PersistedRawAttachment,
    RawMaterializer,
)


UTC = timezone.utc


def _attachment() -> DownloadedAttachment:
    message_id = "message-stable-identity"
    payload = b"private-raw-fixture"
    moment = datetime(2026, 8, 13, 5, 30, tzinfo=UTC)
    message = {
        "openConversationId": "group-fixture",
        "senderOpenDingTalkId": "sender-fixture",
        "openMessageId": message_id,
        "createTime": moment.isoformat().replace("+00:00", "Z"),
        "title": "资金明细",
        "attachments": [{"mediaId": "media-fixture"}],
        "volatileDisplayField": "first-read",
    }
    return DownloadedAttachment(
        message=message,
        message_id=message_id,
        message_id_hash=sha256(message_id.encode("utf-8")).hexdigest(),
        message_at=moment,
        index=0,
        filename="fixture.png",
        family="资金明细",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )


def _persisted(attachment: DownloadedAttachment, message: dict[str, object]) -> PersistedRawAttachment:
    return PersistedRawAttachment(
        message=message,
        message_id=attachment.message_id,
        message_id_hash=attachment.message_id_hash,
        message_at=attachment.message_at,
        index=attachment.index,
        sha256=attachment.sha256,
    )


def test_reopen_accepts_only_noncanonical_envelope_drift(tmp_path) -> None:
    original = _attachment()
    RawMaterializer().stage(tmp_path, (original,))

    replay_message = dict(original.message)
    replay_message["volatileDisplayField"] = "later-read"
    replay = _persisted(original, replay_message)

    reopened = RawMaterializer.hydrate_persisted_raw_attachment(tmp_path, replay)

    assert reopened.payload == original.payload
    assert reopened.message == replay_message


def test_reopen_rejects_changed_media_resource_even_when_other_identity_matches(tmp_path) -> None:
    original = _attachment()
    RawMaterializer().stage(tmp_path, (original,))

    replay_message = dict(original.message)
    replay_message["attachments"] = [{"mediaId": "different-media-resource"}]

    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.hydrate_persisted_raw_attachment(
            tmp_path,
            _persisted(original, replay_message),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("openConversationId", "different-group"),
        ("senderOpenDingTalkId", "different-sender"),
        ("createTime", "2026-08-13T05:31:00Z"),
        ("title", "different-family"),
    ),
)
def test_reopen_rejects_changed_stable_source_identity(tmp_path, field: str, value: str) -> None:
    original = _attachment()
    RawMaterializer().stage(tmp_path, (original,))

    replay_message = dict(original.message)
    replay_message[field] = value

    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.hydrate_persisted_raw_attachment(
            tmp_path,
            _persisted(original, replay_message),
        )
