
from pathlib import Path
import pandas as pd
import numpy as np

from datasets import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

# ====================================
# PATH
# ====================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data" / "toxicity.csv"

SAVE_DIR = (
    BASE_DIR
    / "models"
    / "toxicity_binary_phobert"
    / "final_model"
)

# ====================================
# LOAD DATA
# ====================================

df = pd.read_csv(DATA_PATH)

print("=" * 50)
print("DATASET")
print(df.head())

print("=" * 50)
print(df.info())

print("=" * 50)
print(df["label"].value_counts())

# ====================================
# PREPROCESS
# ====================================

df["text"] = (
    df["text"]
    .astype(str)
    .str.lower()
    .str.strip()
)

# ====================================
# SPLIT
# ====================================

train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42,
)

train_dataset = Dataset.from_pandas(train_df)
test_dataset = Dataset.from_pandas(test_df)

# ====================================
# LOAD MODEL
# ====================================

MODEL_NAME = "vinai/phobert-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,
    id2label={
        0: "NON_TOXIC",
        1: "TOXIC",
    },
    label2id={
        "NON_TOXIC": 0,
        "TOXIC": 1,
    },
)

# ====================================
# TOKENIZE
# ====================================

def tokenize(batch):

    return tokenizer(

        batch["text"],

        truncation=True,

        padding="max_length",

        max_length=128,
    )


train_dataset = train_dataset.map(
    tokenize,
    batched=True,
)

test_dataset = test_dataset.map(
    tokenize,
    batched=True,
)

train_dataset.set_format(
    type="torch",
    columns=[
        "input_ids",
        "attention_mask",
        "label",
    ],
)

test_dataset.set_format(
    type="torch",
    columns=[
        "input_ids",
        "attention_mask",
        "label",
    ],
)

# ====================================
# METRIC
# ====================================

def compute_metrics(eval_pred):

    logits, labels = eval_pred

    preds = np.argmax(logits, axis=-1)

    return {

        "accuracy": accuracy_score(labels, preds),

        "f1": f1_score(labels, preds),

    }

# ====================================
# TRAIN
# ====================================

args = TrainingArguments(

    output_dir=str(BASE_DIR / "results"),

    eval_strategy="epoch",

    save_strategy="epoch",

    learning_rate=2e-5,

    num_train_epochs=3,

    per_device_train_batch_size=8,

    per_device_eval_batch_size=8,

    weight_decay=0.01,

    logging_steps=20,

    load_best_model_at_end=True,

)

trainer = Trainer(

    model=model,

    args=args,

    train_dataset=train_dataset,

    eval_dataset=test_dataset,

    compute_metrics=compute_metrics,

)

trainer.train()

# ====================================
# TEST
# ====================================

metrics = trainer.evaluate()

print("=" * 50)
print(metrics)

# ====================================
# SAVE MODEL
# ====================================

SAVE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

model.save_pretrained(SAVE_DIR)

tokenizer.save_pretrained(SAVE_DIR)

print("=" * 50)
print("MODEL SAVED TO:")
print(SAVE_DIR)
print("=" * 50)
