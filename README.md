# V2HAB Chatbot

Workspace đánh giá hội thoại tiếng Việt theo nhiều tiêu chí cho CSKH và bán hàng, chạy trên một Flask app duy nhất.

`Python` `Flask` `Transformers` `PhoBERT` `XLM-RoBERTa`

## Mục tiêu

Project này giải quyết 2 nhu cầu trong cùng một app:

- Chatbot tư vấn theo ngữ cảnh FPT Shop
- Đánh giá chất lượng hội thoại theo nhiều tiêu chí nội bộ

Toàn bộ UI và API hiện chạy dưới một domain Flask duy nhất. Điều này giúp việc share qua ngrok đơn giản hơn: chỉ cần một link.

## Các tiêu chí đánh giá

- `positivity`: sắc thái tích cực, trung tính hay tiêu cực
- `empathy`: mức độ ghi nhận cảm xúc và bối cảnh khách hàng
- `politeness`: độ lịch sự, mềm mại, tôn trọng
- `toxicity`: dấu hiệu công kích, đổ lỗi, gay gắt
- `resolution`: mức độ rõ ràng của hướng xử lý, next step, owner

Mỗi tiêu chí có pipeline riêng, mapping điểm riêng và output schema thống nhất để dễ mở rộng.

## Kiến trúc hiện tại

App hiện có một entrypoint chính:

- `app.py`: Flask app, WebSocket chat hub, REST API, criterion pages, memory lifecycle

Các phần chính:

- `services/`: inference, model registry, preprocessing, orchestrator, memory, FPT Shop context
- `templates/`: HTML cho hub và criterion workspace
- `static/`: CSS và JS cho giao diện
- `models/`: model artifacts cục bộ
- `data/`: dataset thô, dữ liệu processed và memory runtime

Không còn Streamlit, không còn port `8501`, không còn cần 2 tunnel ngrok.

## Quy ước path

Project đã được chỉnh để dùng path theo repo root thay vì path tuyệt đối theo máy local.

Điều này có nghĩa:

- `MODELS_DIR=models` sẽ được hiểu là `<repo>/models`
- `MEMORY_DIR=data/memory` sẽ được hiểu là `<repo>/data/memory`
- file `.env` được đọc từ repo root

Vì vậy người khác chỉ cần `git clone`, cài dependency và chạy app trong repo là có thể dùng mà không phải sửa path theo máy riêng.

## Tính năng chính

- Chat với assistant theo ngữ cảnh FPT Shop
- Lưu recent conversations và snapshot hội thoại
- Evaluate hội thoại hiện tại theo nhiều tiêu chí
- Mở từng criterion page để review riêng một tiêu chí
- Chạy local model cho sentiment, empathy, politeness, toxicity
- Fallback heuristic cho resolution nếu thiếu model local
- Có thể share ra ngoài bằng một ngrok URL duy nhất

## Cấu trúc thư mục

```text
.
|-- app.py
|-- requirements.txt
|-- README.md
|-- services/
|-- templates/
|-- static/
|-- models/
|-- data/
|-- train_sentiment_phobert_notebook.ipynb
|-- train_empathy_pseudolabel_xlm_roberta_notebook.ipynb
|-- train_politeness_xlm_roberta_notebook.ipynb
|-- train_binary_toxicity_victsd_phobert_notebook.ipynb
`-- train_problem_resolution_xlm_roberta_notebook.ipynb
```

## Cài đặt

### 1. Tạo môi trường

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Cài dependency

```powershell
pip install -r requirements.txt
```

`requirements.txt` hiện là bản đầy đủ cho cả app runtime lẫn notebook/train cơ bản.

## Cấu hình

Copy-Item .env.example .env

Ví dụ:

```env
APP_HOST=127.0.0.1
APP_PORT=8001
APP_DEBUG=1
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
NGROK_ENABLED=0
NGROK_AUTHTOKEN=
MODELS_DIR=models
MEMORY_DIR=data/memory
REDIS_URL=
REDIS_TTL_SECONDS=86400
```

Ý nghĩa các biến quan trọng:

- `APP_HOST`, `APP_PORT`: host và port chạy Flask
- `GEMINI_API_KEY`: cần cho luồng chatbot tư vấn và tổng hợp bằng Gemini
- `NGROK_ENABLED=1`: bật public URL qua ngrok
- `NGROK_AUTHTOKEN`: authtoken ngrok
- `MODELS_DIR`: thư mục chứa model local
- `MEMORY_DIR`: thư mục lưu snapshot hội thoại
- `REDIS_URL`: optional, nếu muốn thêm cache hoặc memory layer ngoài filesystem

Lưu ý:

- Nếu không có `GEMINI_API_KEY`, phần đánh giá local vẫn có thể chạy nếu model local sẵn sàng.
- Nếu `NGROK_ENABLED=1`, app sẽ in ra đúng một public URL để share.

## Chạy app

```powershell
python app.py
```

Local URL mặc định:

```text
http://127.0.0.1:8001
```

Nếu bật ngrok:

- terminal sẽ in ra một app URL duy nhất
- gửi đúng URL đó cho người khác test

## Giao diện chính

### Hub `/`

Hub là màn hình chính để:

- chat với assistant
- xem recent conversations
- evaluate cả thread hiện tại
- xem insight theo từng criterion

### Criterion pages `/criterion/<criterion>`

Các trang:

- `/criterion/positivity`
- `/criterion/empathy`
- `/criterion/politeness`
- `/criterion/toxicity`
- `/criterion/resolution`

Mỗi trang chỉ evaluate đúng một tiêu chí và gọi trực tiếp Flask API tương ứng.

## API chính

### Web và config

- `GET /`
- `GET /criterion/<criterion>`
- `GET /api/config`
- `GET /api/conversations`

### Chat và evaluate

- `POST /api/chat`
- `POST /api/criterion/<criterion>/evaluate`
- `POST /api/criterion/positivity/chat`
- `WS /ws/chat`

## Output schema

Mỗi criterion evaluator trả về schema gần như sau:

```json
{
  "criterion": "positivity",
  "label": "Sentiment",
  "score": 1,
  "confidence": 0.91,
  "summary": "Hoi thoai dang mang sac thai tieu cuc.",
  "raw_label": "negative",
  "probabilities": {
    "negative": 0.91,
    "neutral": 0.06,
    "positive": 0.03
  },
  "status": "model",
  "model_hint": "models/sentiment_phobert/final_model"
}
```

Schema này giúp dễ cắm vào:

- QA dashboard
- reviewer tool
- batch scoring script
- orchestration layer khác về sau

## Model hiện có

Repo hiện có local artifacts cho:

- sentiment
- empathy
- politeness
- toxicity

Riêng `resolution`:

- logic đã có trong code
- nếu chưa có local model artifact, app sẽ fallback sang heuristic scorer

## Memory và dữ liệu runtime

Conversation memory được lưu dưới `data/memory/`.

Thông thường sẽ có:

- recent conversations
- snapshot theo conversation
- append-only messages
- workflow memory payloads

Điều này có nghĩa repo có thể chứa dữ liệu runtime từ các lần chạy trước, không phải snapshot training-only hoàn toàn sạch.

## Dữ liệu huấn luyện

Thư mục `data/` được chia theo mục đích:

- `data/raw/main_train/`: dataset train chính
- `data/raw/auxiliary_pretrain_baseline/`: dữ liệu baseline hoặc pretrain phụ trợ
- `data/raw/needs_relabel/`: dữ liệu cần relabel cho tiêu chí nội bộ
- `data/processed/`: guideline và template annotation

Notebook huấn luyện hiện có:

- `train_sentiment_phobert_notebook.ipynb`
- `train_empathy_pseudolabel_xlm_roberta_notebook.ipynb`
- `train_politeness_xlm_roberta_notebook.ipynb`
- `train_binary_toxicity_victsd_phobert_notebook.ipynb`
- `train_problem_resolution_xlm_roberta_notebook.ipynb`

## Workflow đề xuất

### Demo và inference

1. Cài dependency
2. Cấu hình `.env`
3. Chạy `python app.py`
4. Mở `http://127.0.0.1:8001`
5. Nếu cần share, bật ngrok và dùng đúng một public URL

### Phát triển model

1. Xem dataset trong `data/raw/`
2. Fine-tune notebook phù hợp với criterion
3. Export model vào `models/<model_name>/final_model`
4. Kiểm tra mapping trong `services/model_registry.py`
5. Chạy lại app để validate prediction trên hub hoặc criterion page

## Hạn chế hiện tại

- `resolution` chưa chắc có đủ local artifact trong repo hiện tại
- Chưa có test coverage đầy đủ cho preprocessing và evaluator API
- Chưa có Docker setup chuẩn cho deployment
- Repo có thể còn dữ liệu memory từ các lần chạy trước

## Hướng mở rộng

- Bổ sung local model hoàn chỉnh cho `resolution`
- Thêm batch inference script
- Thêm test tự động cho API và preprocessing
- Chuẩn hóa experiment tracking
- Đóng gói deployment bằng Docker

## License

Repo hiện chưa có file license.

Nếu bạn định phát hành public hoặc dùng nội bộ bài bản, nên thêm license rõ ràng như `MIT`.
