from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ConversationMemoryService:
    def __init__(
        self,
        *,
        memory_dir: Path,
        redis_url: str = "",
        redis_ttl_seconds: int = 86400,
    ) -> None:
        self._memory_dir = memory_dir
        self._conversation_dir = self._memory_dir / "conversations"
        self._recent_path = self._memory_dir / "recent_conversations.json"
        self._lock = Lock()
        self._redis_ttl_seconds = max(60, int(redis_ttl_seconds))
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._conversation_dir.mkdir(parents=True, exist_ok=True)
        self._redis_client = self._build_redis_client(redis_url)

    def load_all_snapshots(self) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for path in self._conversation_dir.glob("*/snapshot.json"):
            try:
                snapshots.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        snapshots.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return snapshots

    def load_snapshot(self, conversation_id: str) -> dict[str, Any] | None:
        snapshot = self._load_snapshot_from_redis(conversation_id)
        if snapshot is not None:
            return snapshot

        path = self._snapshot_path(conversation_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        conversation_id = str(snapshot.get("id") or "").strip()
        if not conversation_id:
            return

        with self._lock:
            self._snapshot_path(conversation_id).parent.mkdir(parents=True, exist_ok=True)
            self._snapshot_path(conversation_id).write_text(
                json.dumps(snapshot, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            self._write_messages_jsonl(conversation_id, snapshot.get("messages") or [])
            self._upsert_recent_index(snapshot)
            self._save_snapshot_to_redis(snapshot)

    def list_recent_conversations(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._load_recent_index()
        rows.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return rows[:limit]

    def append_workflow_memory(self, conversation_id: str, memory_key: str, payload: dict[str, Any]) -> None:
        row = {
            "conversation_id": conversation_id,
            "memory_key": memory_key,
            "payload": payload,
            "updated_at": utc_now_iso(),
        }
        path = self._workflow_memory_path(conversation_id, memory_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=True, indent=2), encoding="utf-8")
        self._save_workflow_memory_to_redis(conversation_id, memory_key, row)

    def get_workflow_memory(self, conversation_id: str, memory_key: str) -> dict[str, Any] | None:
        payload = self._get_workflow_memory_from_redis(conversation_id, memory_key)
        if payload is not None:
            return payload
        path = self._workflow_memory_path(conversation_id, memory_key)
        if not path.exists():
            return None
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        payload = row.get("payload")
        return payload if isinstance(payload, dict) else None

    def append_message(self, conversation_id: str, message: dict[str, Any]) -> None:
        self._append_message_to_redis(conversation_id, message)
        path = self._messages_path(conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=True) + "\n")

    def _build_redis_client(self, redis_url: str):
        normalized = redis_url.strip()
        if redis is None or not normalized:
            return None
        try:
            client = redis.Redis.from_url(normalized, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def _snapshot_path(self, conversation_id: str) -> Path:
        return self._conversation_dir / conversation_id / "snapshot.json"

    def _messages_path(self, conversation_id: str) -> Path:
        return self._conversation_dir / conversation_id / "messages.jsonl"

    def _workflow_memory_path(self, conversation_id: str, memory_key: str) -> Path:
        safe_key = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in memory_key)
        return self._conversation_dir / conversation_id / "workflow_memory" / f"{safe_key}.json"

    def _load_recent_index(self) -> list[dict[str, Any]]:
        if not self._recent_path.exists():
            return []
        try:
            payload = json.loads(self._recent_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _upsert_recent_index(self, snapshot: dict[str, Any]) -> None:
        items = [item for item in self._load_recent_index() if item.get("id") != snapshot.get("id")]
        items.insert(
            0,
            {
                "id": snapshot.get("id"),
                "title": snapshot.get("title"),
                "preview": snapshot.get("preview"),
                "message_count": snapshot.get("message_count"),
                "created_at": snapshot.get("created_at"),
                "updated_at": snapshot.get("updated_at"),
            },
        )
        self._recent_path.write_text(json.dumps(items[:100], ensure_ascii=True, indent=2), encoding="utf-8")

    def _write_messages_jsonl(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        path = self._messages_path(conversation_id)
        with path.open("w", encoding="utf-8") as handle:
            for message in messages:
                handle.write(json.dumps(message, ensure_ascii=True) + "\n")

    def _save_snapshot_to_redis(self, snapshot: dict[str, Any]) -> None:
        if self._redis_client is None:
            return
        conversation_id = str(snapshot.get("id") or "").strip()
        if not conversation_id:
            return
        try:
            self._redis_client.set(
                f"conversation_snapshot:{conversation_id}",
                json.dumps(snapshot, ensure_ascii=True),
                ex=self._redis_ttl_seconds,
            )
            score = datetime.fromisoformat(str(snapshot.get("updated_at") or utc_now_iso())).timestamp()
            self._redis_client.zadd("recent_conversations", {conversation_id: score})
            self._redis_client.expire("recent_conversations", self._redis_ttl_seconds)
        except Exception:
            return

    def _load_snapshot_from_redis(self, conversation_id: str) -> dict[str, Any] | None:
        if self._redis_client is None:
            return None
        try:
            payload = self._redis_client.get(f"conversation_snapshot:{conversation_id}")
            if not payload:
                return None
            return json.loads(payload)
        except Exception:
            return None

    def _append_message_to_redis(self, conversation_id: str, message: dict[str, Any]) -> None:
        if self._redis_client is None:
            return
        try:
            key = f"conversation_messages:{conversation_id}"
            self._redis_client.rpush(key, json.dumps(message, ensure_ascii=True))
            self._redis_client.expire(key, self._redis_ttl_seconds)
        except Exception:
            return

    def _save_workflow_memory_to_redis(self, conversation_id: str, memory_key: str, row: dict[str, Any]) -> None:
        if self._redis_client is None:
            return
        try:
            key = f"conversation_workflow_memory:{conversation_id}"
            self._redis_client.hset(key, memory_key, json.dumps(row, ensure_ascii=True))
            self._redis_client.expire(key, self._redis_ttl_seconds)
        except Exception:
            return

    def _get_workflow_memory_from_redis(self, conversation_id: str, memory_key: str) -> dict[str, Any] | None:
        if self._redis_client is None:
            return None
        try:
            raw = self._redis_client.hget(f"conversation_workflow_memory:{conversation_id}", memory_key)
            if not raw:
                return None
            row = json.loads(raw)
        except Exception:
            return None
        payload = row.get("payload")
        return payload if isinstance(payload, dict) else None


def build_default_memory_service(base_dir: Path) -> ConversationMemoryService:
    memory_dir = base_dir / os.getenv("MEMORY_DIR", "data/memory")
    redis_url = os.getenv("REDIS_URL", "").strip()
    redis_ttl = int(os.getenv("REDIS_TTL_SECONDS", "86400"))
    return ConversationMemoryService(
        memory_dir=memory_dir,
        redis_url=redis_url,
        redis_ttl_seconds=redis_ttl,
    )
