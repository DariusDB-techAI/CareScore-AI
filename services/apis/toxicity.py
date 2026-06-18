from pathlib import Path

from services.local_model_runner import get_classifier

MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "models"
    / "toxicity_binary_phobert"
    / "final_model"
)

classifier = get_classifier(MODEL_DIR)


def evaluate_toxicity(transcript: str):

    result = classifier.predict(transcript)

    confidence = float(result["confidence"])

    score = round(confidence * 5, 2)

    label = result["label"]

    summary = (
        "Phát hiện nội dung Toxic."
        if label.upper() == "TOXIC"
        else "Không phát hiện nội dung Toxic."
    )

    return {
        "criterion": "toxicity",
        "score": score,
        "summary": summary,
        "raw_label": label,
        "confidence": confidence,
        "probabilities": result.get("probabilities", {}),
        "model_hint": "PhoBERT",
        "status": "Completed",
    }