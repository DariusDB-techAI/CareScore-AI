# AI Conversation Quality Studio

Giao dien demo cho he thong danh gia chat luong hoi thoai khach hang bang `Flask` + `WebSocket`.

## Tinh nang hien tai

- Giao dien chat kieu ChatGPT.
- Sidebar luu danh sach hoi thoai.
- 5 nut danh gia theo tung tieu chi.
- Dashboard cho quan ly voi KPI va chart.
- Chatbot ho tro:
  - `gemini`
  - `mock`

## Chay du an

```bash
pip install -r requirements.txt
python app.py
```

Mo:

- `http://127.0.0.1:8001/`
- `http://127.0.0.1:8001/dashboard`

## Chatbot provider

### 1. Gemini API

PowerShell:

```powershell
$env:CHAT_PROVIDER="gemini"
$env:GEMINI_API_KEY="your_gemini_api_key"
$env:GEMINI_MODEL="gemini-3.5-flash-lite"
$env:GEMINI_FALLBACK_MODELS="gemini-2.5-flash-lite"
python app.py
```

### 2. Mock tam thoi

```powershell
$env:CHAT_PROVIDER="mock"
python app.py
```

## Ghi chu model Gemini

App hien uu tien model `gemini-3.5-flash-lite` theo cau hinh ban muon.
Neu model nay khong available tren tai khoan/region, backend se fallback tu dong sang `gemini-2.5-flash-lite`.

Nguon chinh thuc:
- https://ai.google.dev/gemini-api/docs/models/gemini-v2
- https://ai.google.dev/docs/gemini_api_overview/

## Cam model danh gia sau nay

Hien tai backend danh gia van dung `run_mock_model()` trong `app/__init__.py`.
API hien tai:

- `POST /api/evaluate/<conversation_id>/<criterion>`
