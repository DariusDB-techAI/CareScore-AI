# AI Conversation Quality Studio

Giao dien demo cho he thong danh gia chat luong hoi thoai khach hang bang `Flask` + `WebSocket`.

## Tinh nang hien tai

- Giao dien chat kieu ChatGPT.
- Sidebar luu danh sach hoi thoai.
- 5 nut danh gia theo tung tieu chi:
  - Cam xuc tong the
  - Muc do dong cam
  - Lich su va ton trong
  - Ngon ngu tieu cuc/cong kich
  - Kha nang giai quyet van de
- Moi tieu chi co theme giao dien rieng khi bam.
- Dashboard cho quan ly:
  - KPI tong so hoi thoai
  - KPI tong so luot danh gia
  - KPI diem trung binh
  - Bieu do cot
  - Bieu do radar
  - Danh sach tom tat tung hoi thoai
- Chatbot ho tro 3 provider:
  - `mock`
  - `openai`
  - `ollama`

## Chay du an

```bash
pip install -r requirements.txt
python app.py
```

Mo:

- `http://127.0.0.1:8001/` de chat va danh gia
- `http://127.0.0.1:8001/dashboard` de xem dashboard

## Chatbot provider

### 1. OpenAI API

PowerShell:

```powershell
$env:CHAT_PROVIDER="openai"
$env:OPENAI_API_KEY="your_api_key"
$env:OPENAI_MODEL="chat-latest"
python app.py
```

### 2. Llama local qua Ollama

Can co Ollama dang chay tren may:

```powershell
ollama run llama3.1
```

Sau do:

```powershell
$env:CHAT_PROVIDER="ollama"
$env:OLLAMA_MODEL="llama3.1"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
python app.py
```

### 3. Mock tam thoi

```powershell
$env:CHAT_PROVIDER="mock"
python app.py
```

## Ghi chu OpenAI

- `gpt-3.5-turbo` la model legacy/deprecated.
- `gpt-3.5-turbo-instruct` la model cu cho legacy endpoint.
- Neu muon trai nghiem gan ChatGPT hon, nen dung `chat-latest` hoac doi `OPENAI_MODEL` sang model OpenAI moi hon.

## Cam model danh gia sau nay

Hien tai backend danh gia van dung `run_mock_model()` trong `app/__init__.py`.

Ban co the thay the moi tieu chi bang logic nhu:

```python
import joblib

model = joblib.load("models/sentiment.pkl")
score = model.predict([transcript])[0]
```

Hoac voi `.h5`:

```python
from tensorflow.keras.models import load_model

model = load_model("models/empathy.h5")
score = model.predict(...)
```

API hien tai tach theo dang:

- `POST /api/evaluate/<conversation_id>/<criterion>`
