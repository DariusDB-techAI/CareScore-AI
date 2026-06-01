from __future__ import annotations

import os
import random
import uuid
from datetime import datetime
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


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
Ban la mot nhan vien cham soc khach hang tieng Viet.
Muc tieu:
- Tra loi ro rang, lich su, dong cam.
- Neu khach hang dang buc xuc, truoc tien ghi nhan va xin loi neu phu hop.
- Khong boi dat thong tin. Neu thieu du lieu, hoi them 1-2 chi tiet can thiet.
- Uu tien de xuat buoc xu ly cu the.
- Tra loi gon, tu nhien, giong mot tro ly chat hien dai.
""".strip()

CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "mock").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "chat-latest").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1").strip()
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "45"))

_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if OpenAI is None:
        raise RuntimeError("OpenAI package is not installed")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    if _openai_client is None:
        _openai_client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)
    return _openai_client


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
                "openai_model": OPENAI_MODEL,
                "ollama_model": OLLAMA_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
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

        conversation = process_user_message(payload.get("conversation_id"), user_message)
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
    if role == "user" and len(conversation["messages"]) == 1:
        conversation["title"] = content[:40] if content else conversation["title"]


@socketio.on("connect")
def handle_connect():
    emit("system", {"status": "connected"})


@socketio.on("send_message")
def handle_send_message(payload: dict[str, Any]):
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return

    conversation = process_user_message(payload.get("conversation_id"), user_message)
    emit("message", {"conversation_id": conversation["id"], "message": conversation["messages"][-2]})
    emit("message", {"conversation_id": conversation["id"], "message": conversation["messages"][-1]})
    emit("conversation_updated", conversation, broadcast=True)


def process_user_message(conversation_id: str | None, user_message: str) -> dict[str, Any]:
    conversation = ensure_conversation(conversation_id)
    add_message(conversation, "user", user_message)
    bot_reply = generate_chatbot_reply(conversation)
    add_message(conversation, "assistant", bot_reply)
    return conversation


def generate_chatbot_reply(conversation: dict[str, Any]) -> str:
    provider = CHAT_PROVIDER
    try:
        if provider == "openai":
            return generate_openai_reply(conversation)
        if provider == "ollama":
            return generate_ollama_reply(conversation)
    except Exception as exc:
        return (
            f"Khong the goi provider '{provider}': {exc}. "
            "He thong da fallback sang che do tra loi mau tam thoi."
        )

    return build_mock_reply(conversation["messages"][-1]["content"])


def conversation_to_llm_messages(conversation: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": CHATBOT_SYSTEM_PROMPT}]
    for message in conversation["messages"]:
        if message["role"] not in {"user", "assistant"}:
            continue
        messages.append({"role": message["role"], "content": message["content"]})
    return messages


def generate_openai_reply(conversation: dict[str, Any]) -> str:
    client = get_openai_client()
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=conversation_to_llm_messages(conversation),
        temperature=0.6,
    )
    text = getattr(response, "output_text", "") or ""
    if text.strip():
        return text.strip()
    raise RuntimeError("OpenAI response did not contain output_text")


def generate_ollama_reply(conversation: dict[str, Any]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": conversation_to_llm_messages(conversation),
        "stream": False,
        "options": {
            "temperature": 0.6,
        },
    }
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=OPENAI_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content", "").strip()
    if content:
        return content
    raise RuntimeError("Ollama response did not contain message.content")


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
