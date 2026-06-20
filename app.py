from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from flask_sock import Sock
from google import genai
from google.genai import types

from services.agent import build_agent_context, build_fallback_reply, extract_transcript, is_agent_request
from services.conversation_memory import build_default_memory_service
from services.evaluation import CRITERIA_META
from services.fptshop_context import FPTShopContextService
from services.google_ai import (
    describe_gemini_api_key_issue,
    get_gemini_api_key,
    get_gemini_model,
    is_gemini_configured,
    validate_gemini_api_key,
)
from services.ngrok_helper import start_ngrok_tunnel
from services.paths import PROJECT_ROOT


BASE_DIR = PROJECT_ROOT


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


load_local_env()

app = Flask(__name__)
sock = Sock(app)
FPTSHOP_CONTEXT_SERVICE = FPTShopContextService()


def get_app_host() -> str:
    return os.getenv("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"


def get_app_port() -> int:
    return int(os.getenv("APP_PORT", "8001").strip() or "8001")


def get_app_debug() -> bool:
    return (os.getenv("APP_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"})


def is_ngrok_enabled() -> bool:
    return (os.getenv("NGROK_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"})


def get_ngrok_authtoken() -> str:
    return os.getenv("NGROK_AUTHTOKEN", "").strip()


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def resolve_server_port(host: str, preferred_port: int, max_attempts: int = 20) -> int:
    if port_is_available(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, preferred_port + max_attempts + 1):
        if port_is_available(host, port):
            print(f"Cong {preferred_port} dang duoc su dung. App se chuyen sang cong {port}.")
            return port

    raise RuntimeError(f"Khong tim duoc cong trong khoang {preferred_port}-{preferred_port + max_attempts}.")


def start_public_tunnel(app_port: int) -> str | None:
    if not is_ngrok_enabled():
        return None

    authtoken = get_ngrok_authtoken()
    return start_ngrok_tunnel(authtoken=authtoken, port=app_port)


CRITERIA = []
for key, value in CRITERIA_META.items():
    CRITERIA.append(
        {
            "id": key,
            "label": value["label"],
            "description": value["summary"],
            "prompt": f"Hay danh gia hoi thoai nay theo tieu chi {value['label'].lower()}:",
            "theme": "criterion",
            "has_page": True,
            "href": f"/criterion/{key}",
        }
    )

CRITERION_THEMES = {
    "positivity": {
        "title": "Sentiment Studio",
        "eyebrow": "Warm Signal",
        "accent": "#ff7a00",
        "accent_soft": "rgba(255, 122, 0, 0.14)",
        "bg_start": "#fff3e8",
        "bg_end": "#ffe1bf",
        "surface": "#fffaf4",
        "ink": "#311300",
        "muted": "#7a4b27",
        "chip": "#ffd5ad",
        "placeholder": "Vi du:\nKhach hang: Toi that vong ve don hang nay.\nNhan vien: Em xin loi vi trai nghiem nay...",
        "button_label": "Evaluate sentiment",
        "focus_points": ["positive", "neutral", "negative"],
        "support_copy": "Ho tro nhap tu don, cau ngan, hoac transcript hoi thoai day du.",
    },
    "empathy": {
        "title": "Empathy Garden",
        "eyebrow": "Listening Lens",
        "accent": "#0f9d7a",
        "accent_soft": "rgba(15, 157, 122, 0.15)",
        "bg_start": "#e8fff8",
        "bg_end": "#cbf7e6",
        "surface": "#f7fffb",
        "ink": "#07271f",
        "muted": "#42695f",
        "chip": "#c9f1e4",
        "placeholder": "Vi du:\nKhach hang: Toi rat met vi phai doi qua lau.\nNhan vien: Em hieu su bat tien nay va se kiem tra ngay...",
        "button_label": "Evaluate empathy",
        "focus_points": ["dong cam", "boi canh", "ho tro tiep"],
        "support_copy": "Kiem tra viec ghi nhan cam xuc, nhac lai boi canh va chuyen sang huong ho tro.",
    },
    "politeness": {
        "title": "Politeness Atelier",
        "eyebrow": "Tone Craft",
        "accent": "#0d5bd7",
        "accent_soft": "rgba(13, 91, 215, 0.14)",
        "bg_start": "#eef4ff",
        "bg_end": "#dce7ff",
        "surface": "#fbfdff",
        "ink": "#0c1933",
        "muted": "#4f638c",
        "chip": "#d6e4ff",
        "placeholder": "Vi du:\nKhach hang: Toi can duoc giai thich phi nay.\nNhan vien: Em xin phep kiem tra lai cho anh chi...",
        "button_label": "Evaluate politeness",
        "focus_points": ["xung ho", "ton trong", "phan hoi mem"],
        "support_copy": "Do do ton trong, do mem va cach giu tone giao tiep chuyen nghiep.",
    },
    "toxicity": {
        "title": "Toxicity Watchtower",
        "eyebrow": "Risk Scan",
        "accent": "#c62828",
        "accent_soft": "rgba(198, 40, 40, 0.14)",
        "bg_start": "#fff0ef",
        "bg_end": "#ffd7d3",
        "surface": "#fff8f7",
        "ink": "#341111",
        "muted": "#885151",
        "chip": "#ffd6d2",
        "placeholder": "Vi du:\nKhach hang: Toi rat buc xuc.\nNhan vien: Anh dang noi chuyen kieu gi day?",
        "button_label": "Evaluate toxicity",
        "focus_points": ["cong kich", "do loi", "gay gat"],
        "support_copy": "Criterion nay can doc ky summary vi model dang tim dau hieu doc hai hoac tan cong.",
    },
    "resolution": {
        "title": "Resolution Control Room",
        "eyebrow": "Next Step Check",
        "accent": "#7057ff",
        "accent_soft": "rgba(112, 87, 255, 0.14)",
        "bg_start": "#f4f0ff",
        "bg_end": "#e1d9ff",
        "surface": "#fbfaff",
        "ink": "#1d173b",
        "muted": "#5f5890",
        "chip": "#ddd7ff",
        "placeholder": "Vi du:\nKhach hang: Don cua toi bi tre.\nNhan vien: Em da tao yeu cau kiem tra va se goi lai truoc 17h hom nay.",
        "button_label": "Evaluate resolution",
        "focus_points": ["next step", "deadline", "owner"],
        "support_copy": "Tap trung vao huong xu ly, nguoi phu trach va moc thoi gian cu the.",
    },
}

CONVERSATIONS: dict[str, list[dict[str, object]]] = {}
CONVERSATION_META: dict[str, dict[str, str]] = {}
CRITERION_CONVERSATIONS: dict[str, dict[str, list[dict[str, object]]]] = {
    "positivity": {},
}
MEMORY_SERVICE = build_default_memory_service(BASE_DIR)


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


def bootstrap_conversations_from_memory() -> None:
    for snapshot in MEMORY_SERVICE.load_all_snapshots():
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


bootstrap_conversations_from_memory()


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


def persist_conversation_snapshot(conversation_id: str) -> None:
    messages = CONVERSATIONS.get(conversation_id)
    if messages is None:
        return
    MEMORY_SERVICE.save_snapshot(serialize_conversation_detail(conversation_id, messages))


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


def get_latest_advisor_context(messages: list[dict[str, object]]) -> dict[str, object] | None:
    for message in reversed(messages):
        advisor_context = message.get("advisor_context")
        if isinstance(advisor_context, dict):
            return advisor_context
    return None


def build_fptshop_system_prompt(advisor_context: dict[str, object]) -> str:
    snippets = advisor_context.get("snippets") if isinstance(advisor_context.get("snippets"), list) else []
    matched_categories = (
        advisor_context.get("matched_categories") if isinstance(advisor_context.get("matched_categories"), list) else []
    )
    snippet_text = "\n".join(f"- {str(item)}" for item in snippets[:8])
    category_text = ", ".join(str(item) for item in matched_categories) if matched_categories else "chua xac dinh"
    source_url = str(advisor_context.get("source") or FPTSHOP_CONTEXT_SERVICE.HOMEPAGE_URL)
    homepage_status = str(advisor_context.get("homepage_status") or "unavailable")
    return f"""
Ban la nhan vien tu van ban hang va cham soc khach hang cua FPT Shop.
Nhiem vu:
- Tu van bang tieng Viet, tap trung vao cac san pham va nhu cau lien quan den FPT Shop.
- Uu tien dua tren context lay tu website FPT Shop duoc cung cap ben duoi.
- Neu khach chua noi ro nhu cau, hay hoi them toi da 2 cau ngan de lam ro ngan sach, muc dich dung, thuong hieu, hoac phan khuc.
- Neu khach hoi ve gia, khuyen mai, ton kho, bao hanh, tra gop ma context khong co du lieu cu the, hay noi ro ban chua thay thong tin do trong context hien tai va huong khach vao {source_url}.
- Khong boi dat chinh sach, khuyen mai, ton kho, thong so, qua tang, thoi gian giao hang.
- Neu cau hoi khong lien quan den FPT Shop hoac mua sam/CSKH, hay lich su giai thich ban chi ho tro cac noi dung lien quan FPT Shop.
- Khong dung Markdown.
- Khong su dung cac ky hieu dinh dang nhu #, *, **, _, -, bullet list.
- Tra loi gon, ro, thuc dung, giong nhan vien tu van.

Context FPT Shop:
source={source_url}
homepage_status={homepage_status}
matched_categories={category_text}
website_snippets:
{snippet_text if snippet_text else "- Khong lay duoc snippet cu the tu website luc nay."}
""".strip()


def get_chat_config() -> dict[str, str | bool]:
    api_key = get_gemini_api_key()
    return {
        "api_key": api_key,
        "model": get_gemini_model(),
        "configured": is_gemini_configured(),
        "config_error": describe_gemini_api_key_issue(api_key),
    }


def generate_reply(
    messages: list[dict[str, object]],
    *,
    system_prompt: str | None = None,
) -> str:
    config = get_chat_config()
    if not config["configured"]:
        raise RuntimeError(str(config["config_error"] or "GEMINI_API_KEY chua hop le."))

    client = genai.Client(api_key=validate_gemini_api_key())
    contents: list[types.Content] = []
    for message in messages:
        role = message["role"]
        text = message["content"]
        if role == "user":
            contents.append(types.UserContent(parts=[types.Part(text=text)]))
        else:
            contents.append(types.ModelContent(parts=[types.Part(text=text)]))

    response = client.models.generate_content(
        model=str(config["model"]),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt or build_fptshop_system_prompt({}),
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=700,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini khong tra ve noi dung text.")
    return sanitize_markdownish_text(text)


def generate_evaluation_reply(
    *,
    user_message: str,
    transcript: str,
    evaluation: dict[str, object],
) -> str:
    evaluation_context = build_agent_context(evaluation)
    fallback_reply = build_fallback_reply(evaluation)
    prompt = (
        "Duoi day la yeu cau cua nguoi dung, transcript hoi thoai can danh gia, "
        "va output tu agent orchestrator sau khi route qua cac local model theo tieu chi phu hop.\n\n"
        f"User message:\n{user_message}\n\n"
        f"Transcript:\n{transcript}\n\n"
        f"Evaluation output:\n{evaluation_context}\n\n"
        "Yeu cau bat buoc cho cau tra loi cuoi:\n"
        "1. Phai ket luan ro hoi thoai nay dang tot hay chua tot.\n"
        "2. Phai noi ro co dau hieu toxicity hay khong.\n"
        "3. Phai tom tat cac diem manh va diem can cai thien dua tren cac tieu chi da duoc route.\n"
        "4. Phai dua ra cac de xuat cai thien cu the cho nhan vien/chatbot.\n"
        "5. Khong duoc bo qua ket qua cua bat ky tieu chi nao da co trong evaluation output.\n"
        "6. Tra loi bang van ban thuong, gon, ro, truc dien.\n\n"
        f"Neu can, day la mau thong tin toi thieu phai bao phu: {fallback_reply}"
    )
    try:
        reply = generate_reply(
            [{"role": "user", "content": prompt}],
            system_prompt=(
                "Ban la chatbot tong hop ket qua danh gia hoi thoai cho UI. "
                "Ban khong tu danh gia lai, chi dien giai output da co tu agent orchestrator va local models. "
                "Cau tra loi phai noi du 4 nhom y: ket luan tong quan, toxicity neu co, diem manh va diem yeu, de xuat cai thien. "
                "Neu mot tieu chi co diem thap hoac xau, phai noi thang dieu do. "
                "Neu toxicity khong phat hien hoac khong noi bat, phai noi ro dieu do. "
                "Khong duoc bo sung nhan xet ngoai evaluation output. "
                "Khong dung Markdown."
            ),
        )
    except RuntimeError:
        return fallback_reply

    normalized_reply = " ".join(reply.lower().split())
    required_signals = ["cai thien", "toxic"]
    if any(signal not in normalized_reply for signal in required_signals):
        return fallback_reply
    return reply


def sanitize_markdownish_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue

        while line.startswith("#"):
            line = line[1:].lstrip()

        if line.startswith(("- ", "* ", "+ ")):
            line = line[2:].lstrip()

        if len(line) > 2 and line[0].isdigit():
            dot_index = line.find(". ")
            if dot_index > 0 and line[:dot_index].isdigit():
                line = line[dot_index + 2 :].lstrip()

        replacements = [
            ("**", ""),
            ("__", ""),
            ("`", ""),
            ("*", ""),
            ("_", ""),
        ]
        for old, new in replacements:
            line = line.replace(old, new)

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def append_assistant_message(
    messages: list[dict[str, object]],
    content: str,
    agent_result: dict[str, object] | None = None,
    advisor_context: dict[str, object] | None = None,
    message_kind: str = "chat",
) -> None:
    message: dict[str, object] = {
        "role": "assistant",
        "content": content,
        "created_at": utc_now_iso(),
        "message_kind": message_kind,
    }
    if agent_result is not None:
        message["agent_result"] = agent_result
    if advisor_context is not None:
        message["advisor_context"] = advisor_context
    messages.append(message)


def run_hub_chat(conversation_id: str, message: str) -> dict[str, object]:
    from services.evaluator_orchestrator import run_orchestrated_evaluation

    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("Message is required.")

    ensure_conversation_meta(conversation_id)
    messages = CONVERSATIONS.setdefault(conversation_id, [])
    user_message = {"role": "user", "content": cleaned_message, "created_at": utc_now_iso()}
    messages.append(user_message)
    MEMORY_SERVICE.append_message(conversation_id, user_message)
    touch_conversation(conversation_id)

    agent_payload: dict[str, object] | None = None
    agent_result: dict[str, object] | None = None
    advisor_context: dict[str, object] | None = None
    try:
        if is_agent_request(cleaned_message):
            transcript = extract_transcript(cleaned_message)
            agent_result = run_orchestrated_evaluation(
                transcript=transcript,
                user_prompt=cleaned_message,
                selected_criteria=None,
            )
            agent_payload = {
                "transcript": transcript,
                "evaluation": agent_result,
                "fallback_reply": build_fallback_reply(agent_result),
            }
            reply = generate_evaluation_reply(
                user_message=cleaned_message,
                transcript=transcript,
                evaluation=agent_result,
            )
        else:
            advisor_context = FPTSHOP_CONTEXT_SERVICE.build_context(cleaned_message)
            reply = generate_reply(messages, system_prompt=build_fptshop_system_prompt(advisor_context))
    except RuntimeError as exc:
        if agent_result is not None:
            reply = str(agent_payload["fallback_reply"]) if agent_payload is not None else str(exc)
            append_assistant_message(messages, reply, agent_result, advisor_context)
            touch_conversation(conversation_id)
            MEMORY_SERVICE.append_workflow_memory(
                conversation_id,
                "last_evaluator_plan",
                {
                    "message": cleaned_message,
                    "agent_result": agent_result,
                    "updated_at": utc_now_iso(),
                },
            )
            persist_conversation_snapshot(conversation_id)
            return {
                "conversation_id": conversation_id,
                "messages": messages,
                "conversation": serialize_conversation_detail(conversation_id, messages),
                "conversations": list_conversation_summaries(),
            }
        messages.pop()
        touch_conversation(conversation_id)
        persist_conversation_snapshot(conversation_id)
        raise
    except Exception:
        messages.pop()
        touch_conversation(conversation_id)
        persist_conversation_snapshot(conversation_id)
        raise

    append_assistant_message(messages, reply, agent_result, advisor_context)
    touch_conversation(conversation_id)
    MEMORY_SERVICE.append_workflow_memory(
        conversation_id,
        "last_hub_reply",
        {
            "user_message": cleaned_message,
            "reply": reply,
            "has_agent_result": agent_result is not None,
            "advisor_context": advisor_context or {},
            "updated_at": utc_now_iso(),
        },
    )
    persist_conversation_snapshot(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "conversation": serialize_conversation_detail(conversation_id, messages),
        "conversations": list_conversation_summaries(),
    }


def run_panel_evaluation(
    conversation_id: str,
    criteria: list[str] | None = None,
    prompt: str = "",
) -> dict[str, object]:
    from services.evaluator_orchestrator import run_orchestrated_evaluation

    messages = CONVERSATIONS.get(conversation_id)
    if messages is None:
        raise ValueError("Khong tim thay hoi thoai can danh gia.")

    transcript = build_transcript_from_messages(messages)
    if not transcript:
        raise ValueError("Hoi thoai hien tai chua co noi dung de danh gia.")

    selected_criteria = [item for item in (criteria or []) if item in CRITERIA_META]
    evaluation = run_orchestrated_evaluation(
        transcript=transcript,
        user_prompt=prompt,
        selected_criteria=selected_criteria or None,
    )
    reply = generate_evaluation_reply(
        user_message=prompt.strip() or "Hay danh gia cuoc hoi thoai nay va de xuat huong cai thien.",
        transcript=transcript,
        evaluation=evaluation,
    )
    append_assistant_message(
        messages,
        reply,
        evaluation,
        None,
        message_kind="evaluation",
    )
    touch_conversation(conversation_id)
    MEMORY_SERVICE.append_workflow_memory(
        conversation_id,
        "last_evaluator_plan",
        {
            "prompt": prompt,
            "orchestrator": evaluation.get("orchestrator"),
            "selected_criteria": evaluation.get("orchestrator", {}).get("selected_criteria", []),
            "preprocess_log": evaluation.get("preprocess_log"),
            "reply": reply,
            "updated_at": utc_now_iso(),
        },
    )
    conversation = serialize_conversation_detail(conversation_id, messages)
    MEMORY_SERVICE.save_snapshot(conversation)
    return {
        "conversation_id": conversation_id,
        "criteria": evaluation["orchestrator"]["selected_criteria"],
        "prompt": prompt,
        "evaluation": evaluation,
        "reply": reply,
        "conversation": conversation,
        "messages": messages,
        "conversations": list_conversation_summaries(),
    }


def build_single_criterion_context(criterion: str, evaluation: dict[str, object]) -> str:
    return (
        f"Criterion={criterion}\n"
        f"Score={evaluation['score']}/5\n"
        f"Confidence={evaluation['confidence']}\n"
        f"RawLabel={evaluation['raw_label']}\n"
        f"Summary={evaluation['summary']}\n"
        f"Status={evaluation['status']}\n"
        f"ModelHint={evaluation['model_hint']}"
    )


def build_single_criterion_fallback_reply(criterion: str, evaluation: dict[str, object]) -> str:
    label = CRITERIA_META[criterion]["label"]
    return (
        f"Da danh gia hoi thoai theo tieu chi {label}. "
        f"Ket qua hien tai la {evaluation['score']}/5. "
        f"{evaluation['summary']} "
        f"Nhan model la {evaluation['raw_label']} voi do tin cay {round(float(evaluation['confidence']) * 100)} phan tram."
    )


def run_single_criterion_chat(criterion: str, user_message: str) -> tuple[str, dict[str, object]]:
    from services.evaluation import evaluate_criterion_text

    transcript = extract_transcript(user_message)
    evaluation = evaluate_criterion_text(transcript, criterion)
    context = build_single_criterion_context(criterion, evaluation)
    criterion_label = CRITERIA_META[criterion]["label"]
    prompt = (
        f"Hay tra loi cho nguoi dung chi trong pham vi tieu chi {criterion_label}.\n"
        "Khong danh gia cac tieu chi khac.\n"
        "Duoi day la noi dung user gui va ket qua local model.\n\n"
        f"User message:\n{user_message}\n\n"
        f"Local result:\n{context}"
    )

    reply = generate_reply(
        [{"role": "user", "content": prompt}],
        system_prompt=(
            f"Ban la tro ly phan tich hoi thoai chi cho tieu chi {criterion_label}. "
            "Chi duoc dien giai ket qua local model cua tieu chi nay. "
            "Khong duoc nhac sang tieu chi khac. "
            "Tra loi ngan gon, ro rang, khong dung Markdown."
        ),
    )
    return reply, evaluation


@app.route("/")
def index():
    return render_template("index.html", criteria=CRITERIA, ws_path="/ws/chat")


@app.get("/criterion/<criterion>")
def criterion_page(criterion: str):
    selected = next((item for item in CRITERIA if item["id"] == criterion), None)
    if selected is None:
        return jsonify({"error": "Criterion page not found."}), 404
    theme = CRITERION_THEMES[criterion]
    return render_template(
        "criterion.html",
        criterion=selected,
        criterion_theme=theme,
    )


@app.post("/api/criterion/<criterion>/evaluate")
def api_criterion_evaluate(criterion: str):
    if criterion not in CRITERIA_META:
        return jsonify({"error": "Criterion not found."}), 404

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()

    from services.evaluation import evaluate_criterion_text

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
    return jsonify(
        {
            "model": config["model"],
            "configured": config["configured"],
        }
    )


@app.get("/api/conversations")
def api_conversations():
    return jsonify(list_conversation_summaries())


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    conversation_id = str(payload.get("conversation_id") or "default")
    message = str(payload.get("message") or "").strip()
    try:
        return jsonify(run_hub_chat(conversation_id, message))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


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
                ws.send(
                    json.dumps(
                        {
                            "type": "recent",
                            "request_id": request_id,
                            "conversations": list_conversation_summaries(),
                        }
                    )
                )
                continue

            if message_type == "load_conversation":
                conversation_id = str(payload.get("conversation_id") or "").strip()
                messages = CONVERSATIONS.get(conversation_id)
                if not conversation_id:
                    raise ValueError("Khong tim thay hoi thoai can mo.")
                if messages is None:
                    snapshot = MEMORY_SERVICE.load_snapshot(conversation_id)
                    if snapshot is None:
                        raise ValueError("Khong tim thay hoi thoai can mo.")
                    loaded_messages = snapshot.get("messages")
                    if not isinstance(loaded_messages, list):
                        raise ValueError("Hoi thoai da luu bi loi dinh dang.")
                    CONVERSATIONS[conversation_id] = loaded_messages
                    CONVERSATION_META[conversation_id] = {
                        "created_at": str(snapshot.get("created_at") or utc_now_iso()),
                        "updated_at": str(snapshot.get("updated_at") or utc_now_iso()),
                    }
                    messages = loaded_messages
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
                result = run_panel_evaluation(conversation_id, [str(item) for item in criteria], prompt)
                ws.send(
                    json.dumps(
                        {
                            "type": "evaluation",
                            "request_id": request_id,
                            **result,
                        }
                    )
                )
                continue

            if message_type != "chat":
                raise ValueError("Unsupported websocket message type.")

            conversation_id = str(payload.get("conversation_id") or "default")
            message = str(payload.get("message") or "")
            result = run_hub_chat(conversation_id, message)
            ws.send(
                json.dumps(
                    {
                        "type": "chat",
                        "request_id": request_id,
                        **result,
                    }
                )
            )
        except Exception as exc:
            ws.send(
                json.dumps(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "error": str(exc),
                    }
                )
            )


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
        from services.evaluation import evaluate_criterion_text

        evaluation = evaluate_criterion_text(extract_transcript(message), criterion)
        reply = build_single_criterion_fallback_reply(criterion, evaluation)
    except Exception as exc:
        messages.pop()
        return jsonify({"error": str(exc)}), 500

    append_assistant_message(messages, reply, evaluation)
    return jsonify({"conversation_id": conversation_id, "messages": messages})


if __name__ == "__main__":
    app_host = get_app_host()
    app_port = resolve_server_port(app_host, get_app_port())
    app_debug = get_app_debug()

    if is_ngrok_enabled():
        try:
            app_public_url = start_public_tunnel(app_port)
            if app_public_url:
                print(f"Ngrok App URL: {app_public_url}")
                print(f"Cho may khac dung URL nay de vao app: {app_public_url}")
        except RuntimeError as exc:
            print(f"Canh bao: {exc}")
            print(f"App se tiep tuc chay local tai http://{app_host}:{app_port}")

    app.run(
        host=app_host,
        port=app_port,
        debug=app_debug,
        use_reloader=False if is_ngrok_enabled() else app_debug,
    )
