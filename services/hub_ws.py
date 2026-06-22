from __future__ import annotations

import json

from .hub_chat import run_hub_chat, run_panel_evaluation
from .hub_conversations import list_conversation_summaries, load_conversation_snapshot, serialize_conversation_detail


def register_ws(sock, memory_service) -> None:
    @sock.route("/ws/chat")
    def ws_chat(ws) -> None:
        while True:
            raw_message = ws.receive()
            if raw_message is None:
                break

            request_id = None
            try:
                payload = json.loads(raw_message)
                request_id = payload.get("request_id")
                message_type = str(payload.get("type") or "chat")

                if message_type == "recent":
                    ws.send(json.dumps({"type": "recent", "request_id": request_id, "conversations": list_conversation_summaries()}))
                    continue

                if message_type == "load_conversation":
                    conversation_id = str(payload.get("conversation_id") or "").strip()
                    messages = load_conversation_snapshot(memory_service, conversation_id)
                    ws.send(
                        json.dumps(
                            {
                                "type": "conversation",
                                "request_id": request_id,
                                "conversation": serialize_conversation_detail(conversation_id, messages),
                            }
                        )
                    )
                    continue

                if message_type == "evaluate":
                    conversation_id = str(payload.get("conversation_id") or "").strip()
                    criteria = payload.get("criteria")
                    prompt = str(payload.get("prompt") or "")
                    if not isinstance(criteria, list):
                        criteria = []
                    result = run_panel_evaluation(memory_service, conversation_id, [str(item) for item in criteria], prompt)
                    ws.send(json.dumps({"type": "evaluation", "request_id": request_id, **result}))
                    continue

                if message_type != "chat":
                    raise ValueError("Unsupported websocket message type.")

                conversation_id = str(payload.get("conversation_id") or "default")
                message = str(payload.get("message") or "")
                result = run_hub_chat(memory_service, conversation_id, message)
                ws.send(json.dumps({"type": "chat", "request_id": request_id, **result}))
            except Exception as exc:
                ws.send(json.dumps({"type": "error", "request_id": request_id, "error": str(exc)}))
