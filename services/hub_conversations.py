from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .conversation_memory import ConversationMemoryService, build_default_memory_service


CONVERSATIONS: dict[str, list[dict[str, object]]] = {}
CONVERSATION_META: dict[str, dict[str, str]] = {}
CRITERION_CONVERSATIONS: dict[str, dict[str, list[dict[str, object]]]] = {
    "positivity": {},
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_conversation_meta(conversation_id: str) -> dict[str, str]:
    return CONVERSATION_META.setdefault(
        conversation_id,
        {
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        },
    )


def touch_conversation(conversation_id: str) -> None:
    meta = ensure_conversation_meta(conversation_id)
    meta["updated_at"] = utc_now_iso()


def build_conversation_title(messages: list[dict[str, object]]) -> str:
    first_user_message = next(
        (str(item["content"]).strip() for item in messages if item.get("role") == "user" and str(item.get("content", "")).strip()),
        "",
    )
    if not first_user_message:
        return "Cuoc hoi thoai moi"
    single_line = " ".join(first_user_message.split())
    return single_line[:48] + ("..." if len(single_line) > 48 else "")


def build_conversation_preview(messages: list[dict[str, object]]) -> str:
    last_message = next(
        (str(item["content"]).strip() for item in reversed(messages) if str(item.get("content", "")).strip()),
        "",
    )
    if not last_message:
        return "Chua co noi dung."
    single_line = " ".join(last_message.split())
    return single_line[:88] + ("..." if len(single_line) > 88 else "")


def get_latest_agent_result(messages: list[dict[str, object]]) -> dict[str, object] | None:
    for message in reversed(messages):
        agent_result = message.get("agent_result")
        if isinstance(agent_result, dict):
            return agent_result
    return None


def get_latest_advisor_context(messages: list[dict[str, object]]) -> dict[str, object] | None:
    for message in reversed(messages):
        advisor_context = message.get("advisor_context")
        if isinstance(advisor_context, dict):
            return advisor_context
    return None


def serialize_conversation_summary(conversation_id: str, messages: list[dict[str, object]]) -> dict[str, object]:
    meta = ensure_conversation_meta(conversation_id)
    return {
        "id": conversation_id,
        "title": build_conversation_title(messages),
        "preview": build_conversation_preview(messages),
        "message_count": len(messages),
        "created_at": meta["created_at"],
        "updated_at": meta["updated_at"],
    }


def serialize_conversation_detail(conversation_id: str, messages: list[dict[str, object]]) -> dict[str, object]:
    payload = serialize_conversation_summary(conversation_id, messages)
    payload["messages"] = messages
    payload["latest_agent_result"] = get_latest_agent_result(messages)
    payload["latest_advisor_context"] = get_latest_advisor_context(messages)
    return payload


def list_conversation_summaries() -> list[dict[str, object]]:
    return sorted(
        [serialize_conversation_summary(conversation_id, messages) for conversation_id, messages in CONVERSATIONS.items()],
        key=lambda item: str(item["updated_at"]),
        reverse=True,
    )


def build_transcript_from_messages(messages: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for message in messages:
        if str(message.get("message_kind") or "chat") != "chat":
            continue
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        speaker = "Customer" if role == "user" else "Agent"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines).strip()


def load_conversation_snapshot(memory_service: ConversationMemoryService, conversation_id: str) -> list[dict[str, object]]:
    normalized_id = str(conversation_id or "").strip()
    if not normalized_id:
        raise ValueError("Khong tim thay hoi thoai can mo.")

    messages = CONVERSATIONS.get(normalized_id)
    if messages is not None:
        return messages

    snapshot = memory_service.load_snapshot(normalized_id)
    if snapshot is None:
        raise ValueError("Khong tim thay hoi thoai can mo.")

    loaded_messages = snapshot.get("messages")
    if not isinstance(loaded_messages, list):
        raise ValueError("Hoi thoai da luu bi loi dinh dang.")

    CONVERSATIONS[normalized_id] = loaded_messages
    CONVERSATION_META[normalized_id] = {
        "created_at": str(snapshot.get("created_at") or utc_now_iso()),
        "updated_at": str(snapshot.get("updated_at") or utc_now_iso()),
    }
    return loaded_messages


def bootstrap_conversations_from_memory(memory_service: ConversationMemoryService) -> None:
    for snapshot in memory_service.load_all_snapshots():
        conversation_id = str(snapshot.get("id") or "").strip()
        if not conversation_id:
            continue
        messages = snapshot.get("messages")
        if not isinstance(messages, list):
            continue
        CONVERSATIONS[conversation_id] = messages
        CONVERSATION_META[conversation_id] = {
            "created_at": str(snapshot.get("created_at") or utc_now_iso()),
            "updated_at": str(snapshot.get("updated_at") or utc_now_iso()),
        }


def persist_conversation_snapshot(memory_service: ConversationMemoryService, conversation_id: str) -> None:
    messages = CONVERSATIONS.get(conversation_id)
    if messages is None:
        return
    memory_service.save_snapshot(serialize_conversation_detail(conversation_id, messages))


def build_memory_service(base_dir: Path) -> ConversationMemoryService:
    memory_service = build_default_memory_service(base_dir)
    bootstrap_conversations_from_memory(memory_service)
    return memory_service
