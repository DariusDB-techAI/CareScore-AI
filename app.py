from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from services import run_quality_agent
from services.agent import extract_transcript, is_agent_request
from services.evaluation import CRITERIA_META


BASE_DIR = Path(__file__).resolve().parent


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

CHAT_SYSTEM_PROMPT = """
Ban la tro ly ho tro danh gia chat luong hoi thoai cham soc khach hang bang tieng Viet.
Nhiem vu:
- Tra loi ro rang, ngan gon, huu ich.
- Neu nguoi dung muon danh gia hoi thoai theo tieu chi nao, hay tap trung vao tieu chi do.
- Neu da co ket qua danh gia tu local models, hay dua vao ket qua do de tong hop cho nguoi dung.
- Co the dua ra nhan xet, goi y sua cau tra loi, va de xuat buoc xu ly tiep theo.
- Khong boi dat thong tin khong co trong hoi thoai.
- Khong dung Markdown.
- Khong su dung cac ky hieu dinh dang nhu #, *, **, _, -, bullet list.
- Tra loi bang van ban thuong, co the xuong dong nhung khong them ky hieu trang tri.
""".strip()

CRITERIA = []
for key, value in CRITERIA_META.items():
    CRITERIA.append(
        {
            "id": key,
            "label": value["label"],
            "description": value["summary"],
            "prompt": f"Hay danh gia hoi thoai nay theo tieu chi {value['label'].lower()}:",
            "theme": "criterion",
            "has_page": key in ["positivity", "toxicity"],
            "href": f"/criterion/{key}",
        }
    )

CONVERSATIONS: dict[str, list[dict[str, object]]] = {}
CRITERION_CONVERSATIONS: dict[str, dict[str, list[dict[str, object]]]] = {
    "positivity": {},
    "toxicity": {},
}


def get_chat_config() -> dict[str, str | bool]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    placeholder_values = {
        "",
        "your_api_key_here",
        "paste_your_key_here",
        "changeme",
    }
    return {
        "api_key": api_key,
        "model": model,
        "configured": api_key not in placeholder_values,
    }


def generate_reply(messages: list[dict[str, object]]) -> str:
    config = get_chat_config()
    if not config["configured"]:
        raise RuntimeError(
            "GEMINI_API_KEY chua hop le. Mo file .env va thay 'your_api_key_here' bang API key Gemini that."
        )

    client = genai.Client(api_key=str(config["api_key"]))
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
            system_instruction=CHAT_SYSTEM_PROMPT,
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=700,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini khong tra ve noi dung text.")
    return sanitize_markdownish_text(text)


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
) -> None:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if agent_result is not None:
        message["agent_result"] = agent_result
    messages.append(message)


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

    reply = generate_reply([{"role": "user", "content": prompt}])
    return reply, evaluation


@app.route("/")
def index():
    return render_template("index.html", criteria=CRITERIA)


@app.get("/criterion/positivity")
def positivity_page():
    criterion = next(item for item in CRITERIA if item["id"] == "positivity")
    return render_template("positivity.html", criterion=criterion)

@app.get("/criterion/toxicity")
def toxicity_page():
    criterion = next(item for item in CRITERIA if item["id"] == "toxicity")
    return render_template("toxicity.html", criterion=criterion)

@app.get("/api/config")
def api_config():
    config = get_chat_config()
    return jsonify(
        {
            "model": config["model"],
            "configured": config["configured"],
        }
    )


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    conversation_id = str(payload.get("conversation_id") or "default")
    message = str(payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    messages = CONVERSATIONS.setdefault(conversation_id, [])
    messages.append({"role": "user", "content": message})

    agent_payload: dict[str, object] | None = None
    agent_result: dict[str, object] | None = None
    try:
        if is_agent_request(message):
            agent_payload = run_quality_agent(message)
            agent_result = agent_payload["evaluation"]
            contextual_message = {
                "role": "user",
                "content": (
                    f"{message}\n\n"
                    "Su dung ket qua danh gia local model sau day de tra loi:\n"
                    f"{agent_payload['agent_context']}"
                ),
            }
            reply = generate_reply([*messages[:-1], contextual_message])
        else:
            reply = generate_reply(messages)
    except RuntimeError as exc:
        if agent_result is not None:
            reply = str(agent_payload["fallback_reply"]) if agent_payload is not None else str(exc)
            append_assistant_message(messages, reply, agent_result)
            return jsonify({"conversation_id": conversation_id, "messages": messages})
        messages.pop()
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        messages.pop()
        return jsonify({"error": str(exc)}), 500

    append_assistant_message(messages, reply, agent_result)
    return jsonify({"conversation_id": conversation_id, "messages": messages})


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

@app.post("/api/criterion/toxicity/chat")
def api_criterion_toxicity_chat():

    criterion = "toxicity"

    payload = request.get_json(silent=True) or {}
    conversation_id = str(payload.get("conversation_id") or "default")
    message = str(payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message is required."}), 400

    criterion_conversations = CRITERION_CONVERSATIONS.setdefault(
        criterion,
        {}
    )

    messages = criterion_conversations.setdefault(
        conversation_id,
        []
    )

    messages.append({
        "role": "user",
        "content": message
    })

    try:

        reply, evaluation = run_single_criterion_chat(
            criterion,
            message
        )

    except RuntimeError:

        from services.evaluation import evaluate_criterion_text

        evaluation = evaluate_criterion_text(
            extract_transcript(message),
            criterion
        )

        reply = build_single_criterion_fallback_reply(
            criterion,
            evaluation
        )

    except Exception as exc:

        messages.pop()

        return jsonify({
            "error": str(exc)
        }), 500

    append_assistant_message(
        messages,
        reply,
        evaluation
    )

    return jsonify({

        "conversation_id": conversation_id,

        "messages": messages

    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=True)
