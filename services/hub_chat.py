from __future__ import annotations

from google import genai
from google.genai import types

from .agent import build_agent_context, build_fallback_reply, extract_transcript, is_agent_request
from .evaluation import CRITERIA_META
from .fptshop_context import FPTShopContextService
from .google_ai import (
    describe_gemini_api_key_issue,
    describe_gemini_request_error,
    get_gemini_api_key,
    get_gemini_model,
    is_gemini_configured,
    validate_gemini_api_key,
)
from .hub_conversations import (
    CONVERSATIONS,
    build_transcript_from_messages,
    ensure_conversation_meta,
    list_conversation_summaries,
    persist_conversation_snapshot,
    serialize_conversation_detail,
    touch_conversation,
    utc_now_iso,
)


FPTSHOP_CONTEXT_SERVICE = FPTShopContextService()


def get_chat_config() -> dict[str, str | bool]:
    api_key = get_gemini_api_key()
    return {
        "api_key": api_key,
        "model": get_gemini_model(),
        "configured": is_gemini_configured(),
        "config_error": describe_gemini_api_key_issue(api_key),
    }


def build_fptshop_system_prompt(advisor_context: dict[str, object]) -> str:
    snippets = advisor_context.get("snippets") if isinstance(advisor_context.get("snippets"), list) else []
    matched_categories = advisor_context.get("matched_categories") if isinstance(advisor_context.get("matched_categories"), list) else []
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

        for old, new in [("**", ""), ("__", ""), ("`", ""), ("*", ""), ("_", "")]:
            line = line.replace(old, new)

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def generate_reply(messages: list[dict[str, object]], *, system_prompt: str | None = None) -> str:
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

    try:
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
    except Exception as exc:
        raise RuntimeError(describe_gemini_request_error(exc)) from exc

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini khong tra ve noi dung text.")
    return sanitize_markdownish_text(text)


def generate_evaluation_reply(*, user_message: str, transcript: str, evaluation: dict[str, object]) -> str:
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
    if any(signal not in normalized_reply for signal in ["cai thien", "toxic"]):
        return fallback_reply
    return reply


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


def run_hub_chat(memory_service, conversation_id: str, message: str) -> dict[str, object]:
    from .evaluator_orchestrator import run_orchestrated_evaluation

    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("Message is required.")

    ensure_conversation_meta(conversation_id)
    messages = CONVERSATIONS.setdefault(conversation_id, [])
    user_message = {"role": "user", "content": cleaned_message, "created_at": utc_now_iso()}
    messages.append(user_message)
    memory_service.append_message(conversation_id, user_message)
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
            memory_service.append_workflow_memory(
                conversation_id,
                "last_evaluator_plan",
                {
                    "message": cleaned_message,
                    "agent_result": agent_result,
                    "updated_at": utc_now_iso(),
                },
            )
            persist_conversation_snapshot(memory_service, conversation_id)
            return build_hub_response(conversation_id, messages)
        messages.pop()
        touch_conversation(conversation_id)
        persist_conversation_snapshot(memory_service, conversation_id)
        raise
    except Exception:
        messages.pop()
        touch_conversation(conversation_id)
        persist_conversation_snapshot(memory_service, conversation_id)
        raise

    append_assistant_message(messages, reply, agent_result, advisor_context)
    touch_conversation(conversation_id)
    memory_service.append_workflow_memory(
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
    persist_conversation_snapshot(memory_service, conversation_id)
    return build_hub_response(conversation_id, messages)


def build_hub_response(conversation_id: str, messages: list[dict[str, object]]) -> dict[str, object]:
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "conversation": serialize_conversation_detail(conversation_id, messages),
        "conversations": list_conversation_summaries(),
    }


def run_panel_evaluation(memory_service, conversation_id: str, criteria: list[str] | None = None, prompt: str = "") -> dict[str, object]:
    from .evaluator_orchestrator import run_orchestrated_evaluation

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
    append_assistant_message(messages, reply, evaluation, None, message_kind="evaluation")
    touch_conversation(conversation_id)
    memory_service.append_workflow_memory(
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
    memory_service.save_snapshot(conversation)
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
    from .evaluation import evaluate_criterion_text

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
