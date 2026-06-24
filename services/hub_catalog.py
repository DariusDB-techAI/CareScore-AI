from __future__ import annotations

from .evaluation import CRITERIA_META


CRITERIA = [
    {
        "id": key,
        "label": value["label"],
        "description": value["summary"],
        "prompt": f"Hay danh gia hoi thoai nay theo tieu chi {value['label'].lower()}:",
        "theme": "criterion",
        "has_page": True,
        "href": f"/criterion/{key}",
    }
    for key, value in CRITERIA_META.items()
]


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
       "title": "Đánh Giá Mức Độ Lịch Sự",
       "eyebrow": "POLITENESS ANALYSIS",
       "accent": "#dc2626",
        "accent_soft": "rgba(220,38,38,0.18)",
        "bg_start": "#fee2e2",
        "bg_end": "#fecaca",
        "surface": "#ffffff",
        "ink": "#450a0a",
        "muted": "#7f1d1d",
        "chip": "#fee2e2",
       "placeholder": """Ví dụ:
        Khách hàng: Tôi muốn được giải thích khoản phí này.

        Nhân viên: Dạ em xin phép kiểm tra lại thông tin và phản hồi anh/chị trong ít phút ạ.

        Khách hàng: Cảm ơn em.
        """,

        "button_label": "Đánh giá mức độ lịch sự",
        "focus_points": [
            "Xưng hô phù hợp",
            "Tôn trọng khách hàng",
            "Ngôn ngữ mềm mại",
            "Thái độ chuyên nghiệp"
        ],
        "support_copy": "Đánh giá mức độ lịch sự, cách xưng hô, thái độ phục vụ và khả năng duy trì giao tiếp chuyên nghiệp với khách hàng."
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
