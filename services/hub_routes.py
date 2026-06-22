from __future__ import annotations

from flask import jsonify, render_template, request

from .evaluation import CRITERIA_META
from .hub_catalog import CRITERIA, CRITERION_THEMES
from .hub_chat import get_chat_config, run_hub_chat, run_panel_evaluation, run_single_criterion_chat
from .hub_conversations import (
    CRITERION_CONVERSATIONS,
    list_conversation_summaries,
    load_conversation_snapshot,
    serialize_conversation_detail,
)


def register_routes(app, memory_service) -> None:
    @app.route("/")
    def index():
        return render_template("index.html", criteria=CRITERIA, ws_path="/ws/chat")

    @app.get("/criterion/<criterion>")
    def criterion_page(criterion: str):
        selected = next((item for item in CRITERIA if item["id"] == criterion), None)
        if selected is None:
            return jsonify({"error": "Criterion page not found."}), 404
        return render_template("criterion.html", criterion=selected, criterion_theme=CRITERION_THEMES[criterion])

    @app.post("/api/criterion/<criterion>/evaluate")
    def api_criterion_evaluate(criterion: str):
        if criterion not in CRITERIA_META:
            return jsonify({"error": "Criterion not found."}), 404

        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()

        from .evaluation import evaluate_criterion_text

        try:
            evaluation = evaluate_criterion_text(text, criterion)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

        return jsonify(
            {
                "criterion": criterion,
                "meta": CRITERIA_META[criterion],
                "theme": CRITERION_THEMES[criterion],
                "text": text,
                "evaluation": evaluation,
            }
        )

    @app.get("/api/config")
    def api_config():
        config = get_chat_config()
        return jsonify({"model": config["model"], "configured": config["configured"]})

    @app.get("/api/conversations")
    def api_conversations():
        return jsonify(list_conversation_summaries())

    @app.get("/api/conversations/<conversation_id>")
    def api_conversation_detail(conversation_id: str):
        try:
            messages = load_conversation_snapshot(memory_service, conversation_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(serialize_conversation_detail(conversation_id, messages))

    @app.post("/api/chat")
    def api_chat():
        payload = request.get_json(silent=True) or {}
        conversation_id = str(payload.get("conversation_id") or "default")
        message = str(payload.get("message") or "").strip()
        try:
            return jsonify(run_hub_chat(memory_service, conversation_id, message))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.post("/api/criterion/positivity/chat")
    def api_criterion_positivity_chat():
        criterion = "positivity"
        payload = request.get_json(silent=True) or {}
        conversation_id = str(payload.get("conversation_id") or "default")
        message = str(payload.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Message is required."}), 400

        criterion_conversations = CRITERION_CONVERSATIONS.setdefault(criterion, {})
        messages = criterion_conversations.setdefault(conversation_id, [])
        messages.append({"role": "user", "content": message})

        try:
            reply, evaluation = run_single_criterion_chat(criterion, message)
        except RuntimeError:
            from .evaluation import evaluate_criterion_text
            from .agent import extract_transcript
            from .hub_chat import build_single_criterion_fallback_reply

            evaluation = evaluate_criterion_text(extract_transcript(message), criterion)
            reply = build_single_criterion_fallback_reply(criterion, evaluation)
        except Exception as exc:
            messages.pop()
            return jsonify({"error": str(exc)}), 500

        from .hub_chat import append_assistant_message

        append_assistant_message(messages, reply, evaluation)
        return jsonify({"conversation_id": conversation_id, "messages": messages})
