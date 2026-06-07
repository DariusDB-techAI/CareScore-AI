# Conversation Quality Studio

Project này được tổ chức theo hướng để team có thể làm song song:

- 1 trang tổng có chatbot chung
- agent trên trang tổng có thể route đúng tiêu chí đánh giá
- mỗi tiêu chí có 1 hàm model riêng
- mỗi team có thể tự làm UI/theme của tiêu chí mình
- nhưng phải giữ nguyên một số function và endpoint cố định

README này dùng để bàn giao cho team.

## 1. Mục tiêu hiện tại

Hệ thống có 2 kiểu màn hình:

1. Trang tổng `/`
2. Trang riêng theo tiêu chí, hiện tại mới làm `positivity`

### Trang tổng

Trang tổng có chatbot chung.

User có thể:

- dán hội thoại
- hỏi agent muốn đánh giá positivity
- hỏi agent muốn đánh giá toxicity
- hỏi agent muốn đánh giá empathy
- hỏi agent muốn đánh giá politeness
- hỏi agent muốn đánh giá resolution

Backend sẽ:

1. nhận diện user đang muốn đánh giá tiêu chí nào
2. gọi đúng API/model function của tiêu chí đó
3. lấy kết quả local model
4. đưa kết quả đó vào context
5. chatbot trả lời lại cho user

### Trang riêng theo tiêu chí

Mỗi trang riêng theo tiêu chí cũng có chatbot.

Nhưng khác với trang tổng:

- trang riêng chỉ được đánh giá 1 tiêu chí duy nhất
- backend chỉ được gọi model của tiêu chí đó
- không detect sang tiêu chí khác

Ví dụ:

- `/criterion/positivity`
- endpoint chat của nó là `/api/criterion/positivity/chat`
- backend chỉ được gọi `evaluate_positivity(transcript)`

Hiện tại:

- `positivity` đã có trang riêng
- 4 tiêu chí còn lại chưa làm, team tự copy pattern đó để tiếp tục

## 2. Cấu trúc chính

### File backend chính

- `app.py`
- `services/agent.py`
- `services/evaluation.py`
- `services/criterion_apis.py`
- `services/model_registry.py`
- `services/local_model_runner.py`

### File evaluator theo từng tiêu chí

- `services/apis/positivity.py`
- `services/apis/empathy.py`
- `services/apis/politeness.py`
- `services/apis/toxicity.py`
- `services/apis/resolution.py`

### File UI chính

- `templates/index.html`
- `static/js/app.js`
- `static/css/style.css`

### File UI riêng của positivity

- `templates/positivity.html`
- `static/js/criterion_chat.js`

## 3. Cách chạy project

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Mở:

- `http://127.0.0.1:8001`

## 4. Cấu hình

Sửa `.env`:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
MODELS_DIR=models
```

`MODELS_DIR=models` nghĩa là model được đặt theo path tương đối từ root project.

Ví dụ:

- `models/positivity_phobert/final_model`
- `models/empathy_xlm_roberta/final_model`
- `models/politeness_xlm_roberta/final_model`
- `models/toxicity_binary_phobert/final_model`
- `models/problem_resolution_xlm_roberta/final_model`

## 5. Contract backend bắt buộc

Đây là phần quan trọng nhất. Team có thể đổi UI, đổi bố cục, đổi màu, nhưng không nên phá contract này.

### 5.1. Mỗi tiêu chí phải có 1 function cố định

Mỗi tiêu chí phải có 1 hàm riêng:

- `evaluate_positivity(transcript)`
- `evaluate_empathy(transcript)`
- `evaluate_politeness(transcript)`
- `evaluate_toxicity(transcript)`
- `evaluate_resolution(transcript)`

Input của tất cả các hàm trên:

```python
transcript: str
```

Hàm này chỉ được:

- đánh giá đúng tiêu chí của mình
- gọi đúng model của tiêu chí của mình

Hàm này không được:

- gọi model của tiêu chí khác
- tự route sang tiêu chí khác

### 5.2. Schema output bắt buộc

Tất cả evaluator function phải trả về cùng một schema:

```python
{
    "criterion": "positivity",
    "score": 5,
    "confidence": 0.91,
    "summary": "...",
    "raw_label": "positive",
    "probabilities": {
        "positive": 0.91,
        "neutral": 0.07,
        "negative": 0.02,
    },
    "status": "model",
    "model_hint": "models/positivity_phobert/final_model",
}
```

Ý nghĩa các field:

- `criterion`: tên tiêu chí
- `score`: điểm quy về thang 1, 3, 5 hoặc 0 nếu lỗi/empty
- `confidence`: độ tin cậy
- `summary`: mô tả ngắn gọn cho user
- `raw_label`: label gốc của model
- `probabilities`: xác suất từng nhãn
- `status`: `model`, `empty`, `missing_model`, `error`, `fallback`
- `model_hint`: model path hoặc model id

### 5.3. Router function cố định

Hàm trung tâm để route evaluator là:

- `call_criterion_api(criterion, transcript)`

Hàm này nằm ở:

- `services/criterion_apis.py`

Nhiệm vụ:

1. nhận `criterion`
2. gọi đúng evaluator function của criterion đó
3. trả kết quả lại cho agent

Team không nên đổi tên hàm này.

## 6. Contract frontend bắt buộc

### 6.1. Fixed UI functions trên trang tổng

Trang tổng nên giữ các function frontend sau:

- `openCriterionPage(criterion)`
- `fillCriterionPrompt(criterion)`
- `sendHubMessage(message)`

Ý nghĩa:

- `openCriterionPage(criterion)`
  - click vào nút tiêu chí trên trang tổng thì phải đi qua hàm này
  - hàm này đưa user sang trang riêng của criterion nếu criterion đó đã có page

- `fillCriterionPrompt(criterion)`
  - nếu muốn chèn prompt mẫu vào ô chat thì dùng hàm này

- `sendHubMessage(message)`
  - gửi message của chatbot trang tổng tới endpoint `/api/chat`

Team có thể đổi HTML/CSS như thế nào cũng được, nhưng click trên nút tiêu chí ở trang tổng vẫn phải đi qua `openCriterionPage(criterion)`.

### 6.2. Fixed UI function trên trang riêng theo tiêu chí

Mỗi trang riêng của criterion nên giữ function:

- `sendCriterionMessage(message)`

Nhiệm vụ:

1. lấy message user
2. gọi đúng endpoint chat của criterion page
3. render lại messages trên UI

Ví dụ với positivity:

- file JS: `static/js/criterion_chat.js`
- endpoint: `/api/criterion/positivity/chat`

## 7. Endpoint cố định

### Trang tổng

- `POST /api/chat`

Dùng cho:

- chatbot trên trang tổng
- agent multi-criteria

### Trang riêng theo tiêu chí

Pattern cố định:

- `POST /api/criterion/<criterion>/chat`

Ví dụ:

- `POST /api/criterion/positivity/chat`
- `POST /api/criterion/toxicity/chat`

Rule:

- endpoint này chỉ được gọi model của 1 criterion duy nhất
- không route sang criterion khác

## 8. Team được thay đổi những gì

Team được phép thay đổi:

- bố cục HTML
- màu sắc
- theme
- font
- animation
- card design
- chat layout
- vị trí panel
- copywriting trên giao diện

Team không nên tự ý thay đổi:

- tên evaluator function
- schema output của evaluator
- tên router function `call_criterion_api(...)`
- tên function UI `openCriterionPage(...)`
- pattern endpoint `/api/criterion/<criterion>/chat`

## 9. Pattern để 4 team còn lại copy

Hiện tại `positivity` là mẫu chuẩn để copy.

Muốn làm thêm 1 criterion mới, ví dụ `toxicity`, thì làm 4 việc:

### B1. Tạo evaluator function

Sửa file:

- `services/apis/toxicity.py`

Tạo hoặc hoàn thiện hàm:

- `evaluate_toxicity(transcript)`

### B2. Đăng ký vào router

Sửa file:

- `services/criterion_apis.py`

Đảm bảo `toxicity` đã được map vào:

- `evaluate_toxicity`

### B3. Tạo trang riêng của criterion

Tạo:

- `templates/toxicity.html`

Trang này có chatbot riêng, theme riêng, bố cục riêng đều được.

Nhưng trang này chỉ được dùng criterion `toxicity`.

### B4. Tạo endpoint chat riêng

Sửa `app.py` và tạo:

- `POST /api/criterion/toxicity/chat`

Trong endpoint đó:

1. nhận message
2. extract transcript
3. gọi `evaluate_toxicity(...)`
4. đưa kết quả vào context
5. chatbot trả lời lại user

## 10. Mẫu positivity hiện tại

Đây là mẫu team có thể nhìn theo:

- evaluator: `services/apis/positivity.py`
- router: `services/criterion_apis.py`
- page: `templates/positivity.html`
- page js: `static/js/criterion_chat.js`
- page endpoint: `POST /api/criterion/positivity/chat`

Nếu team làm criterion mới, có thể copy y chang pattern đó và thay:

- criterion name
- evaluator logic
- model path
- route page
- giao diện

### 10.1. Ví dụ positivity đang chạy như thế nào

Đây là flow thực tế của tiêu chí `positivity` trong project hiện tại.

#### A. Ở trang tổng

1. User đứng ở trang `/`
2. User click nút `Positivity`
3. UI bắt buộc đi qua function:
   - `openCriterionPage("positivity")`
4. Function này đưa user sang:
   - `/criterion/positivity`

Ngoài ra nếu user không vào trang riêng mà chat ngay trên trang tổng:

1. User gửi message ở chatbot trang tổng
2. Frontend gọi:
   - `sendHubMessage(message)`
3. Backend nhận tại:
   - `POST /api/chat`
4. Agent detect user đang muốn đánh giá `positivity`
5. Backend route sang:
   - `call_criterion_api("positivity", transcript)`
6. Router gọi:
   - `evaluate_positivity(transcript)`
7. Model positivity trả kết quả
8. Agent lấy kết quả đó làm context
9. Chatbot trả lời lại cho user

Chi tiết hơn:

- Nút `Positivity` đang được render từ:
  - `templates/index.html`
- Dữ liệu của nút này đến từ:
  - `window.APP_BOOTSTRAP.criteria`
- Khi click nút, frontend gọi:
  - `openCriterionPage("positivity")`
- Function này đang nằm trong:
  - `static/js/app.js`
- Route mà function này đưa user tới:
  - `/criterion/positivity`

Nếu user không bấm vào trang riêng mà chat luôn ở trang tổng:

- Ô chat của trang tổng nằm trong:
  - `templates/index.html`
- JS xử lý gửi message nằm trong:
  - `static/js/app.js`
- Function gửi message là:
  - `sendHubMessage(message)`
- Function này gọi:
  - `POST /api/chat`
- Endpoint `/api/chat` nằm trong:
  - `app.py`
- Trong `app.py`, nhánh xử lý agent tổng quát sẽ gọi:
  - `run_quality_agent(message)`
- Hàm này nằm trong:
  - `services/agent.py`
- `run_quality_agent(...)` sẽ:
  1. detect user đang muốn tiêu chí nào
  2. extract transcript
  3. gọi `call_criterion_api("positivity", transcript)` nếu user muốn positivity
- `call_criterion_api(...)` nằm trong:
  - `services/criterion_apis.py`
- `call_criterion_api("positivity", transcript)` sẽ gọi:
  - `evaluate_positivity(transcript)`
- `evaluate_positivity(...)` nằm trong:
  - `services/apis/positivity.py`

#### B. Ở trang riêng positivity

1. User vào:
   - `/criterion/positivity`
2. User chat với positivity chatbot
3. Frontend gọi:
   - `sendCriterionMessage(message)`
4. Hàm này gọi endpoint:
   - `POST /api/criterion/positivity/chat`
5. Backend extract transcript từ message
6. Backend gọi trực tiếp:
   - `evaluate_positivity(transcript)`
7. Kết quả positivity được đưa vào context
8. Chatbot positivity trả lời lại user
9. UI hiển thị:
   - câu trả lời chatbot
   - block kết quả positivity như score, raw label, confidence

Chi tiết hơn:

- Template HTML của trang riêng positivity nằm ở:
  - `templates/positivity.html`
- JS của trang riêng positivity nằm ở:
  - `static/js/criterion_chat.js`
- Trong file HTML này có cấu hình:

```html
<script>
    window.CRITERION_CHAT_CONFIG = {
        criterion: "positivity",
        endpoint: "/api/criterion/positivity/chat",
        title: "Positivity"
    };
</script>
```

Ý nghĩa:

- `criterion = "positivity"`: trang này chỉ làm positivity
- `endpoint = "/api/criterion/positivity/chat"`: mọi message trên trang này chỉ được gửi vào endpoint positivity

Ở frontend:

- ô chat positivity gọi function:
  - `sendCriterionMessage(message)`
- function này nằm trong:
  - `static/js/criterion_chat.js`
- function này đọc:
  - `window.CRITERION_CHAT_CONFIG.endpoint`
- sau đó gọi:
  - `POST /api/criterion/positivity/chat`

Ở backend:

- endpoint này nằm trong:
  - `app.py`
- endpoint đó hiện đang làm đúng các bước:
  1. nhận `message`
  2. extract transcript bằng:
     - `extract_transcript(message)`
  3. gọi:
     - `evaluate_positivity(transcript)`
  4. nhận kết quả positivity
  5. build context cho chatbot
  6. chatbot trả lời lại đúng trong phạm vi positivity

Điểm quan trọng:

- trang riêng positivity không gọi `evaluate_toxicity(...)`
- trang riêng positivity không gọi `evaluate_empathy(...)`
- trang riêng positivity không detect sang tiêu chí khác
- trang riêng positivity chỉ dùng đúng:
  - `evaluate_positivity(transcript)`

### 10.1.1. Dữ liệu đi qua những gì trong positivity

Khi user gửi một hội thoại vào positivity page, dữ liệu đi theo thứ tự:

1. `message` từ textarea của positivity page
2. `sendCriterionMessage(message)` gửi request
3. endpoint `/api/criterion/positivity/chat` nhận request
4. backend convert `message -> transcript`
5. `evaluate_positivity(transcript)` chạy model positivity
6. model trả:
   - `score`
   - `confidence`
   - `raw_label`
   - `probabilities`
   - `summary`
7. backend dùng kết quả đó để tạo câu trả lời chatbot
8. frontend render:
   - message của chatbot
   - block `agent_result`

Ví dụ output thực tế của `evaluate_positivity(transcript)` nên có dạng:

```python
{
    "criterion": "positivity",
    "score": 5,
    "confidence": 0.91,
    "summary": "Hội thoại giữ được sắc thái tích cực trong phần lớn nội dung.",
    "raw_label": "positive",
    "probabilities": {
        "positive": 0.91,
        "neutral": 0.07,
        "negative": 0.02
    },
    "status": "model",
    "model_hint": "models/positivity_phobert/final_model"
}
```

### 10.2. Những function đang cố định trong flow positivity

Đây là các function team không nên đổi tên nếu muốn giữ đúng kiến trúc hiện tại.

#### Backend fixed functions

- `evaluate_positivity(transcript)`
- `call_criterion_api(criterion, transcript)`
- `run_quality_agent(message)`

#### Frontend fixed functions

- `openCriterionPage(criterion)`
- `fillCriterionPrompt(criterion)`
- `sendHubMessage(message)`
- `sendCriterionMessage(message)`
- `renderAgentResult(result)`

Giải thích cực cụ thể:

- `openCriterionPage(criterion)`
  - dùng ở trang tổng
  - nhiệm vụ: chuyển sang trang riêng của tiêu chí
  - ví dụ:
    - `openCriterionPage("positivity")`
    - kết quả: user sang `/criterion/positivity`

- `fillCriterionPrompt(criterion)`
  - dùng ở trang tổng
  - nhiệm vụ: nếu team muốn, có thể chèn prompt mẫu vào ô chat
  - ví dụ:
    - `fillCriterionPrompt("toxicity")`

- `sendHubMessage(message)`
  - dùng ở chatbot trang tổng
  - nhiệm vụ: gửi message tới `/api/chat`

- `sendCriterionMessage(message)`
  - dùng ở chatbot trang riêng của một criterion
  - nhiệm vụ: gửi message tới `/api/criterion/<criterion>/chat`
  - ví dụ với positivity:
    - gửi tới `/api/criterion/positivity/chat`

- `renderAgentResult(result)`
  - dùng để render block score/confidence/raw_label/probabilities lên UI
  - function này giúp UI có thể đổi theme nhưng vẫn hiển thị đúng dữ liệu model

### 10.2.1. Function nào nằm ở file nào

| Function | Vai trò | File |
|---|---|---|
| `openCriterionPage(criterion)` | điều hướng từ trang tổng sang trang tiêu chí | `static/js/app.js` |
| `fillCriterionPrompt(criterion)` | chèn prompt mẫu vào ô chat trang tổng | `static/js/app.js` |
| `sendHubMessage(message)` | gửi chat ở trang tổng | `static/js/app.js` |
| `sendCriterionMessage(message)` | gửi chat ở trang riêng của criterion | `static/js/criterion_chat.js` |
| `renderAgentResult(result)` | render kết quả model lên UI | `static/js/app.js` hoặc `static/js/criterion_chat.js` |
| `run_quality_agent(message)` | agent tổng quát của hub page | `services/agent.py` |
| `call_criterion_api(criterion, transcript)` | route criterion -> evaluator | `services/criterion_apis.py` |
| `evaluate_positivity(transcript)` | evaluator positivity | `services/apis/positivity.py` |

### 10.3. Những file positivity đang tham gia trực tiếp

- `services/apis/positivity.py`
- `services/criterion_apis.py`
- `app.py`
- `templates/index.html`
- `templates/positivity.html`
- `static/js/app.js`
- `static/js/criterion_chat.js`

Vai trò từng file:

- `services/apis/positivity.py`
  - nơi model positivity thực sự được gọi
- `services/criterion_apis.py`
  - map `"positivity"` -> `evaluate_positivity`
- `app.py`
  - chứa endpoint `/api/chat` và `/api/criterion/positivity/chat`
- `templates/index.html`
  - chứa nút positivity trên trang tổng
- `templates/positivity.html`
  - giao diện riêng của positivity page
- `static/js/app.js`
  - xử lý click nút positivity ở trang tổng
- `static/js/criterion_chat.js`
  - xử lý chatbot của positivity page

### 10.4. Nếu team khác muốn làm theo positivity thì copy phần nào

Ví dụ team `toxicity` có thể copy đúng pattern này:

1. copy `services/apis/positivity.py` sang logic của `toxicity`
2. đăng ký `evaluate_toxicity` vào `services/criterion_apis.py`
3. tạo page `templates/toxicity.html`
4. tạo endpoint `POST /api/criterion/toxicity/chat`
5. ở trang tổng, nút toxicity vẫn đi qua:
   - `openCriterionPage("toxicity")`

Như vậy:

- UI có thể đổi hoàn toàn
- nhưng flow function vẫn giữ nguyên
- nên agent và routing không bị vỡ

Ví dụ cụ thể hơn cho team toxicity:

1. tạo file:
   - `services/apis/toxicity.py`
2. viết hàm:
   - `evaluate_toxicity(transcript)`
3. đăng ký trong:
   - `services/criterion_apis.py`
4. tạo page:
   - `templates/toxicity.html`
5. tạo endpoint:
   - `POST /api/criterion/toxicity/chat`
6. trên trang tổng, nút toxicity khi click vẫn phải đi qua:
   - `openCriterionPage("toxicity")`

Nếu làm đúng 6 bước đó thì team toxicity có thể đổi giao diện thoải mái mà không phá kiến trúc chung.

## 11. Giải thích đơn giản cho beginner

Nếu bạn là người mới trong team, hãy nhớ như sau:

- model scoring nằm trong `services/apis/<criterion>.py`
- route trung tâm nằm trong `services/criterion_apis.py`
- chatbot trang tổng nằm trong `app.py` + `templates/index.html` + `static/js/app.js`
- chatbot trang riêng của criterion nằm trong:
  - `templates/<criterion>.html`
  - `static/js/criterion_chat.js`
  - endpoint `/api/criterion/<criterion>/chat`

Chỉ cần giữ đúng contract function và endpoint là bạn có thể thay giao diện tùy ý.

## 12. Checklist bàn giao cho từng team member

Mỗi team member làm criterion của mình thì check:

- Đã có file `services/apis/<criterion>.py`
- Đã có hàm `evaluate_<criterion>(transcript)`
- Đã trả đúng output schema
- Đã đăng ký vào `services/criterion_apis.py`
- Nếu có page riêng, đã có route `/criterion/<criterion>`
- Đã có endpoint `/api/criterion/<criterion>/chat`
- Nút trên trang tổng đã đi qua `openCriterionPage("<criterion>")`

Nếu tất cả đúng, criterion đó được xem là gần xong.
