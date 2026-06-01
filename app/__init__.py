from __future__ import annotations

import os
import random
import uuid
from datetime import datetime
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit


socketio = SocketIO(cors_allowed_origins="*")

CONVERSATIONS: list[dict[str, Any]] = []

CRITERIA = {
    "sentiment": {
        "label": "Cam xuc tong the",
        "theme": "aurora",
        "summary": "Muc do tich cuc hoac tieu cuc cua toan bo cuoc hoi thoai.",
    },
    "empathy": {
        "label": "Muc do dong cam",
        "theme": "sunset",
        "summary": "Danh gia nhan vien co thau hieu cam xuc va van de cua khach hang hay khong.",
    },
    "politeness": {
        "label": "Lich su va ton trong",
        "theme": "ocean",
        "summary": "Kiem tra cach dung tu va thai do giao tiep cua nhan vien.",
    },
    "toxicity": {
        "label": "Ngon ngu tieu cuc/cong kich",
        "theme": "ember",
        "summary": "Phat hien dau hieu cong kich, gay gat, do loi hoac ngon tu tieu cuc.",
    },
    "resolution": {
        "label": "Kha nang giai quyet van de",
        "theme": "forest",
        "summary": "Danh gia cuoc hoi thoai co di den huong xu ly ro rang hay chua.",
    },
}

CHATBOT_SYSTEM_PROMPT = """
Ban la tro ly cham soc khach hang tieng Viet, noi chuyen tu nhien nhu nguoi that.
Muc tieu:
- Tra loi than thien, ro rang, dong cam, khong robot.
- Neu khach hang dang buc xuc, ghi nhan va xin loi phu hop truoc khi dua huong xu ly.
- Khong boi dat du lieu. Neu thieu thong tin, hoi them toi da 2 cau hoi ngan gon.
- Uu tien de xuat buoc tiep theo cu the, de khach co the thuc hien ngay.
- Cau van ngan vua du, tranh lap lai y, tranh li thuyet dai.
""".strip()

CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite").split(",")
    if model.strip()
]
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "45"))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key"
    socketio.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html", criteria=CRITERIA)

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html", criteria=CRITERIA)

    @app.route("/api/conversations")
    def api_conversations():
        return jsonify(CONVERSATIONS)

    @app.route("/api/chatbot-config")
    def api_chatbot_config():
        return jsonify(
            {
                "provider": CHAT_PROVIDER,
                "gemini_model": GEMINI_MODEL,
                "gemini_fallback_models": GEMINI_FALLBACK_MODELS,
                "gemini_configured": bool(GEMINI_API_KEY),
            }
        )

    @app.route("/api/evaluate/<conversation_id>/<criterion>", methods=["POST"])
    def evaluate(conversation_id: str, criterion: str):
        conversation = next((item for item in CONVERSATIONS if item["id"] == conversation_id), None)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        if criterion not in CRITERIA:
            return jsonify({"error": "Criterion not found"}), 404

        result = run_mock_model(conversation, criterion)
        conversation["evaluations"][criterion] = result
        return jsonify(result)

    @app.route("/api/message", methods=["POST"])
    def api_message():
        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        mode = (payload.get("mode") or "gemini").strip().lower()
        local_role = (payload.get("local_role") or "customer").strip().lower()
        conversation, _ = process_user_message(payload.get("conversation_id"), user_message, mode, local_role)
        return jsonify(conversation)

    return app


def ensure_conversation(conversation_id: str | None = None) -> dict[str, Any]:
    if conversation_id:
        existing = next((item for item in CONVERSATIONS if item["id"] == conversation_id), None)
        if existing:
            return existing

    conversation = {
        "id": str(uuid.uuid4()),
        "title": f"Cuoc hoi thoai {len(CONVERSATIONS) + 1}",
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "evaluations": {},
    }
    CONVERSATIONS.insert(0, conversation)
    return conversation


def add_message(conversation: dict[str, Any], role: str, content: str):
    conversation["messages"].append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
    )
    if len(conversation["messages"]) == 1:
        conversation["title"] = content[:40] if content else conversation["title"]


@socketio.on("connect")
def handle_connect():
    emit("system", {"status": "connected"})


@socketio.on("send_message")
def handle_send_message(payload: dict[str, Any]):
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return

    mode = (payload.get("mode") or "gemini").strip().lower()
    local_role = (payload.get("local_role") or "customer").strip().lower()
    conversation, added_messages = process_user_message(payload.get("conversation_id"), user_message, mode, local_role)
    for message in added_messages:
        emit("message", {"conversation_id": conversation["id"], "message": message})
    emit("conversation_updated", conversation, broadcast=True)


def process_user_message(
    conversation_id: str | None,
    user_message: str,
    mode: str = "gemini",
    local_role: str = "customer",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conversation = ensure_conversation(conversation_id)
    if mode == "local":
        mapped_role = "assistant" if local_role == "support" else "user"
        add_message(conversation, mapped_role, user_message)
        return conversation, [conversation["messages"][-1]]

    add_message(conversation, "user", user_message)
    user_turn = conversation["messages"][-1]
    bot_reply = generate_chatbot_reply(conversation)
    add_message(conversation, "assistant", bot_reply)
    return conversation, [user_turn, conversation["messages"][-1]]


def generate_chatbot_reply(conversation: dict[str, Any]) -> str:
    if CHAT_PROVIDER == "mock":
        return build_mock_reply(conversation["messages"][-1]["content"])

    try:
        return generate_gemini_reply(conversation)
    except Exception as exc:
        return (
            f"Khong the goi Gemini: {exc}. "
            "He thong da fallback sang che do tra loi mau tam thoi."
        )


def conversation_to_gemini_parts(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for message in conversation["messages"]:
        if message["role"] == "user":
            role = "user"
        elif message["role"] == "assistant":
            role = "model"
        else:
            continue
        contents.append({"role": role, "parts": [{"text": message["content"]}]})
    return contents


def build_model_candidates() -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for model in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
        if model and model not in seen:
            candidates.append(model)
            seen.add(model)
    return candidates


def generate_gemini_reply(conversation: dict[str, Any]) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    last_error: str = "unknown"
    for model in build_model_candidates():
        url = f"{GEMINI_BASE_URL}/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "systemInstruction": {"parts": [{"text": CHATBOT_SYSTEM_PROMPT}]},
            "contents": conversation_to_gemini_parts(conversation),
            "generationConfig": {
                "temperature": 0.82,
                "topP": 0.95,
                "maxOutputTokens": 768,
            },
        }
        try:
            response = requests.post(url, json=payload, timeout=GEMINI_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini response did not contain candidates")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts).strip()
            if text:
                return text
            raise RuntimeError("Gemini response did not contain text parts")
        except Exception as exc:
            last_error = str(exc)

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def build_mock_reply(user_message: str) -> str:
    lowered = user_message.lower()
    if any(word in lowered for word in ["loi", "complaint", "khong hai long", "buc xuc"]):
        return (
            "Em da ghi nhan van de cua anh/chi. "
            "Em xin loi vi trai nghiem chua tot va se de xuat huong xu ly cu the ngay sau day."
        )
    if any(word in lowered for word in ["gia", "price", "phi"]):
        return "Em se kiem tra thong tin chi phi lien quan va huong dan anh/chi cach toi uu nhat de xu ly."
    return (
        "Em da nhan duoc noi dung cua anh/chi. "
        "Anh/chi co the cung cap them ma don hang hoac boi canh de em ho tro chinh xac hon."
    )


def run_mock_model(conversation: dict[str, Any], criterion: str) -> dict[str, Any]:
    transcript = " ".join(message["content"].lower() for message in conversation["messages"])
    base_score = random.randint(2, 4)
    indicators = {
        "sentiment": 5 if any(word in transcript for word in ["cam on", "ho tro", "tot", "hai long"]) else base_score,
        "empathy": 5 if any(word in transcript for word in ["xin loi", "ghi nhan", "thau hieu"]) else base_score,
        "politeness": 5 if any(word in transcript for word in ["anh/chi", "em", "ho tro"]) else base_score,
        "toxicity": 1 if any(word in transcript for word in ["ngu", "te", "doi loi", "vo ly"]) else 4,
        "resolution": 5 if any(word in transcript for word in ["huong xu ly", "kiem tra", "de xuat"]) else base_score,
    }
    score = indicators[criterion]
    normalized = score if criterion != "toxicity" else max(1, min(5, score))

    insight_map = {
        "sentiment": "Cuoc hoi thoai nghieng ve tich cuc neu khach hang nhan duoc xac nhan va phan hoi ro rang.",
        "empathy": "Tin hieu dong cam xuat hien khi nhan vien xin loi, ghi nhan va phan hoi theo van de cua khach.",
        "politeness": "Van phong lich duoc duy tri khi cach xung ho va ngu dieu on dinh, ton trong.",
        "toxicity": "Diem cao nghia la an toan ve ngon ngu; diem thap can canh bao noi dung gay gat hoac cong kich.",
        "resolution": "Kha nang giai quyet tot khi cuoc trao doi dua ra hanh dong tiep theo cu the.",
    }

    return {
        "criterion": criterion,
        "label": CRITERIA[criterion]["label"],
        "score": normalized,
        "theme": CRITERIA[criterion]["theme"],
        "confidence": round(random.uniform(0.81, 0.96), 2),
        "summary": insight_map[criterion],
        "model_hint": f"Cho phep thay bang model file cho {criterion}.pkl hoac {criterion}.h5",
    }
