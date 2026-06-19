# V2HAB Chatbot

Multi-Criteria Vietnamese Conversation Evaluation Workspace for Customer Service and Sales Support

`Python` `Flask` `Streamlit` `Transformers` `PhoBERT` `XLM-RoBERTa`

## Overview

This repository provides a complete workspace for analyzing Vietnamese customer-service conversations across multiple quality dimensions, while also supporting an FPT Shop advisor chatbot experience.

The project combines:

- Local NLP models for conversation quality scoring
- A Flask hub application for chat, orchestration, and conversation memory
- Streamlit criterion pages for focused single-metric review
- Training notebooks for each evaluation criterion
- Structured dataset folders for pretraining, baseline experimentation, and relabeling

It is designed for use cases such as:

- Customer-service quality assurance
- Agent coaching and post-call review
- Internal conversation benchmarking
- Vietnamese NLP model experimentation
- Retail support assistant prototyping

## Core Idea

Instead of treating a conversation as a single generic classification task, this project evaluates it through separate quality lenses:

- `Sentiment / Positivity`
- `Empathy`
- `Politeness`
- `Toxicity`
- `Problem Resolution`

Each criterion has its own inference path, score mapping, and summary logic. This makes the system more interpretable for QA teams and easier to extend model-by-model.

## Key Features

- Multi-criteria evaluation for Vietnamese conversations
- Local Transformer inference using checked-in model artifacts
- Dedicated criterion APIs with a shared output schema
- Transcript normalization aligned with notebook training format
- Streamlit pages for criterion-specific review
- Flask chat hub with WebSocket-based interaction
- Persistent conversation memory on filesystem, with optional Redis caching
- FPT Shop context enrichment for advisor-style responses
- Training notebooks for sentiment, empathy, politeness, toxicity, and resolution

## Evaluation Criteria

### 1. Sentiment / Positivity
Measures whether the conversation tone is positive, neutral, or negative overall.

### 2. Empathy
Measures whether the agent acknowledges the customer's frustration, context, or emotional state.

### 3. Politeness
Measures respectfulness, tone softness, and communication style.

### 4. Toxicity
Detects aggressive, blaming, hostile, or toxic language.

### 5. Problem Resolution
Measures whether the conversation closes with a clear direction, next step, or owner.

## System Architecture

### Runtime Layer

- `app.py`
  Main Flask application, REST endpoints, WebSocket chat hub, and conversation lifecycle management
- `streamlit_app.py`
  Streamlit container used to render criterion-specific pages
- `pages/`
  Individual Streamlit pages for each criterion
- `services/`
  Model registry, inference, preprocessing, evaluation orchestration, context lookup, and memory

### Model Layer

The runtime loads local models from `models/` through `transformers` and `torch`.

Current model registry:

- `sentiment_phobert`
- `empathy_xlm_roberta`
- `politeness_xlm_roberta`
- `toxicity_binary_phobert`
- `problem_resolution_xlm_roberta` expected by code

Note:

- The repository currently contains local model artifacts for sentiment, empathy, politeness, and toxicity.
- The `resolution` criterion is implemented in code, but if the local resolution model is missing, the app falls back to a heuristic scorer.

### Memory Layer

Conversation state is persisted under `data/memory/`:

- `recent_conversations.json`
- per-conversation `snapshot.json`
- append-only `messages.jsonl`
- workflow memory payloads

Redis is optional and can be enabled through `REDIS_URL`.

## Project Structure

```text
.
|-- app.py
|-- streamlit_app.py
|-- streamlit_shared.py
|-- run_streamlit.ps1
|-- requirements.txt
|-- services/
|   |-- agent.py
|   |-- conversation_memory.py
|   |-- criterion_apis.py
|   |-- evaluation.py
|   |-- fptshop_context.py
|   |-- local_model_runner.py
|   |-- model_registry.py
|   |-- text_preprocess.py
|   `-- apis/
|-- pages/
|   |-- 01_sentiment_page.py
|   |-- 02_empathy_page.py
|   |-- 03_politeness_page.py
|   |-- 04_toxicity_page.py
|   `-- 05_resolution_page.py
|-- templates/
|-- static/
|-- models/
|   |-- sentiment_phobert/
|   |-- empathy_xlm_roberta/
|   |-- politeness_xlm_roberta/
|   `-- toxicity_binary_phobert/
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- memory/
|-- train_sentiment_phobert_notebook.ipynb
|-- train_empathy_pseudolabel_xlm_roberta_notebook.ipynb
|-- train_politeness_xlm_roberta_notebook.ipynb
|-- train_binary_toxicity_victsd_phobert_notebook.ipynb
`-- train_problem_resolution_xlm_roberta_notebook.ipynb
```

## Data Organization

The dataset layout separates data by purpose:

- `data/raw/main_train/`
  Main training datasets used directly for criterion-specific training
- `data/raw/auxiliary_pretrain_baseline/`
  Auxiliary or baseline datasets for pretraining and transfer learning
- `data/raw/needs_relabel/`
  Candidate datasets that require relabeling for this project's custom criteria
- `data/processed/`
  Annotation templates and labeling guides

Included dataset summaries indicate the source, status, and intended criterion. Based on the current repository metadata:

- Sentiment uses Vietnamese sentiment datasets such as `UIT-VSFC` and `anotherpolarbear/vietnamese-sentiment-analysis`
- Empathy uses `EmpatheticDialogues` mirrors and `ESConv`
- Politeness uses `Stanford Politeness`, `polite-guard`, and related corpora
- Toxicity uses Vietnamese datasets such as `ViCTSD`
- Resolution draws from customer-support and task-oriented dialogue datasets, many of which still require relabeling

## Preprocessing Logic

Before inference, transcripts are normalized to match the notebook training style:

- normalize line breaks
- canonicalize speaker prefixes
- merge into a notebook-style conversation string
- lowercase text
- replace URLs, emails, and phone numbers with special tokens
- collapse extra spaces

This logic lives in `services/text_preprocess.py`.

## Training Assets

The repository includes separate notebooks for each criterion:

- `train_sentiment_phobert_notebook.ipynb`
- `train_empathy_pseudolabel_xlm_roberta_notebook.ipynb`
- `train_politeness_xlm_roberta_notebook.ipynb`
- `train_binary_toxicity_victsd_phobert_notebook.ipynb`
- `train_problem_resolution_xlm_roberta_notebook.ipynb`

These notebooks are intended for:

- dataset loading and cleanup
- preprocessing
- label mapping
- fine-tuning Transformer classifiers
- evaluating checkpoints
- exporting final model artifacts into `models/.../final_model`

## How to Run

### Windows PowerShell

```powershell
git clone <YOUR_GITHUB_REPO_URL>
cd <YOUR_REPO_FOLDER>

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
python app.py
streamlit run streamlit_app.py
```

### macOS / Linux

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd <YOUR_REPO_FOLDER>

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
python app.py
streamlit run streamlit_app.py
```

### 2. Configure environment variables

Create `.env` from `.env.example` and update the values you need:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
MODELS_DIR=models
STREAMLIT_BASE_URL=
STREAMLIT_PORT=8501
MEMORY_DIR=data/memory
REDIS_URL=
REDIS_TTL_SECONDS=86400
```

Notes:

- `GEMINI_API_KEY` is required for the advisor/chat generation flow.
- Local criterion evaluation can still work without Gemini if the local models are available.
- `REDIS_URL` is optional.


Default local services:

- Flask hub: `http://127.0.0.1:8001`
- Streamlit criterion workspace: `http://127.0.0.1:8501`

## Main Interfaces

### Flask Hub

The hub UI provides:

- chat with the advisor assistant
- recent conversation history
- conversation evaluation across selected criteria
- FPT Shop context-aware support prompts

### Criterion Pages

Each criterion has a dedicated page rendered via Streamlit and embedded through Flask:

- `/criterion/positivity`
- `/criterion/empathy`
- `/criterion/politeness`
- `/criterion/toxicity`
- `/criterion/resolution`

These pages are useful for focused manual review and debugging one criterion at a time.

## API Surface

Main routes currently exposed by `app.py`:

- `GET /`
- `GET /criterion/<criterion>`
- `GET /api/config`
- `GET /api/conversations`
- `POST /api/chat`
- `POST /api/criterion/positivity/chat`
- `WS /ws/chat`

## Output Schema

Each criterion evaluator returns a shared schema:

```json
{
  "criterion": "positivity",
  "score": 1,
  "confidence": 0.91,
  "summary": "....",
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

This makes it easier to plug the evaluators into:

- QA dashboards
- reviewer tools
- batch scoring pipelines
- future orchestration layers

## Current Repository State

Important implementation notes for anyone reusing this repository:

- Sentiment, empathy, politeness, and toxicity have local model artifacts present in `models/`
- Resolution is implemented at the application level, but the local model artifact is not currently present in this repo snapshot
- The resolution API therefore uses a fallback heuristic when the model is missing
- Conversation memory data already exists in `data/memory/`, so this repository is not a completely clean training-only snapshot
- `git status` could not be inspected in this environment because the repository is marked with a Windows safe-directory ownership warning

## Recommended Workflow

### For inference and demo

1. Install dependencies
2. Configure `.env`
3. Start Streamlit
4. Start Flask
5. Open the Flask hub and test conversations

### For model development

1. Review dataset summaries under `data/raw/`
2. Use the criterion notebook that matches the target task
3. Export the trained model into `models/<model_name>/final_model`
4. Verify that the corresponding entry in `services/model_registry.py` points to the correct directory
5. Re-run the app and validate predictions through the hub or criterion pages

## Future Improvements

- Add a trained local model for `problem_resolution_xlm_roberta`
- Standardize evaluation reports across all notebooks
- Add batch inference scripts for offline dataset scoring
- Add test coverage for preprocessing and evaluator APIs
- Add Docker setup for reproducible deployment
- Introduce clearer experiment tracking and model versioning

## License

No license file is currently included in this repository snapshot.
If you plan to distribute or open-source the project, add an explicit license such as `MIT`.
