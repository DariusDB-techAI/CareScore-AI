from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))


@dataclass(frozen=True)
class CriterionModelSpec:
    criterion: str
    model_dir: Path
    max_length: int
    score_map: dict[str, int]
    high_signal: str
    low_signal: str
    higher_is_better: bool = True

    @property
    def is_available(self) -> bool:
        return (self.model_dir / "config.json").exists() and (
            (self.model_dir / "model.safetensors").exists()
            or (self.model_dir / "pytorch_model.bin").exists()
        )


MODEL_SPECS: dict[str, CriterionModelSpec] = {
    "positivity": CriterionModelSpec(
        criterion="positivity",
        model_dir=DEFAULT_MODELS_DIR / "sentiment_phobert" / "final_model",
        max_length=256,
        score_map={"negative": 1, "neutral": 3, "positive": 5},
        high_signal="Hoi thoai giu duoc sac thai tich cuc trong phan lon noi dung.",
        low_signal="Hoi thoai nghieng ve cam xuc tieu cuc hoac cang thang.",
        higher_is_better=True,
    ),
    "empathy": CriterionModelSpec(
        criterion="empathy",
        model_dir=DEFAULT_MODELS_DIR / "empathy_xlm_roberta" / "final_model",
        max_length=256,
        score_map={"low_empathy": 1, "medium_empathy": 3, "high_empathy": 5},
        high_signal="Ben ho tro co dau hieu ghi nhan va dong cam voi van de cua khach hang.",
        low_signal="Phan hoi chua the hien ro su ghi nhan cam xuc hoac boi canh.",
        higher_is_better=True,
    ),
    "politeness": CriterionModelSpec(
        criterion="politeness",
        model_dir=DEFAULT_MODELS_DIR / "politeness_xlm_roberta" / "final_model",
        max_length=256,
        score_map={"impolite": 1, "neutral": 3, "polite": 5},
        high_signal="Van phong giao tiep giu duoc su ton trong va lich su.",
        low_signal="Cach dien dat co dau hieu thieu mem mai hoac gay doi dau.",
        higher_is_better=True,
    ),
    "toxicity": CriterionModelSpec(
        criterion="toxicity",
        model_dir=DEFAULT_MODELS_DIR / "toxicity_binary_phobert" / "final_model",
        max_length=256,
        score_map={"clean": 1, "toxic": 5},
        high_signal="Co dau hieu ngon ngu gay gat, cong kich, do loi hoac toxic.",
        low_signal="Khong thay dau hieu ngon ngu cong kich hoac doc hai ro rang.",
        higher_is_better=False,
    ),
    "resolution": CriterionModelSpec(
        criterion="resolution",
        model_dir=DEFAULT_MODELS_DIR / "problem_resolution_xlm_roberta" / "final_model",
        max_length=256,
        score_map={"unresolved": 1, "partially_resolved": 3, "resolved": 5},
        high_signal="Hoi thoai dua ra huong xu ly ro rang va next step cu the.",
        low_signal="Hoi thoai chua chot duoc huong xu ly ro rang hoac next step.",
        higher_is_better=True,
    ),
}
