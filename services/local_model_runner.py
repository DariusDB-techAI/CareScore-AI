from __future__ import annotations

import importlib
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any


MODEL_CLASS_PATHS = {
    "roberta": ("transformers.models.roberta.modeling_roberta", "RobertaForSequenceClassification"),
    "xlm-roberta": (
        "transformers.models.xlm_roberta.modeling_xlm_roberta",
        "XLMRobertaForSequenceClassification",
    ),
}

_TRANSFORMERS_PREPARED = False


def _safe_cache_clear(value: object) -> None:
    cache_clear = getattr(value, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def _prepare_transformers():
    global _TRANSFORMERS_PREPARED
    from transformers import AutoConfig, AutoTokenizer
    from transformers import utils as transformers_utils
    from transformers.utils import import_utils as transformers_import_utils
    from transformers.utils import logging as transformers_logging

    if _TRANSFORMERS_PREPARED:
        return AutoConfig, AutoTokenizer

    transformers_logging.disable_progress_bar()
    try:
        import torchvision  # noqa: F401
    except Exception:
        _safe_cache_clear(getattr(transformers_import_utils, "is_torchvision_available", None))
        _safe_cache_clear(getattr(transformers_import_utils, "is_torchvision_v2_available", None))
        transformers_import_utils.is_torchvision_available = lambda: False
        transformers_import_utils.is_torchvision_v2_available = lambda: False
        transformers_utils.is_torchvision_available = lambda: False
        transformers_utils.is_torchvision_v2_available = lambda: False
        sys.modules.pop("torchvision", None)
        sys.modules.pop("torchvision.io", None)
        sys.modules.pop("torchvision.transforms", None)
        sys.modules.pop("torchvision.transforms.functional", None)

    _TRANSFORMERS_PREPARED = True
    return AutoConfig, AutoTokenizer


@lru_cache(maxsize=16)
def load_model_config(model_dir: str):
    AutoConfig, _ = _prepare_transformers()
    return AutoConfig.from_pretrained(model_dir, local_files_only=True)


@lru_cache(maxsize=8)
def resolve_model_class(model_type: str):
    module_path, class_name = MODEL_CLASS_PATHS.get(model_type, (None, None))
    if not module_path or not class_name:
        raise RuntimeError(f"Unsupported local model type: {model_type}")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class LocalTextClassifier:
    def __init__(self, model_dir: Path):
        try:
            import torch
        except Exception as exc:
            raise RuntimeError(f"PyTorch is unavailable: {exc}") from exc

        _, AutoTokenizer = _prepare_transformers()
        self._torch = torch
        self.config = load_model_config(str(model_dir))
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model_class = resolve_model_class(self.config.model_type)
        self.model = model_class.from_pretrained(model_dir, local_files_only=True, config=self.config)
        self.model.eval()

    def predict(self, text: str, max_length: int = 256) -> dict[str, Any]:
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        with self._torch.no_grad():
            logits = self.model(**encoded).logits

        probabilities = self._torch.softmax(logits, dim=-1)[0]
        prediction_index = int(self._torch.argmax(probabilities).item())
        confidence = float(probabilities[prediction_index].item())
        id2label = self.config.id2label or self.model.config.id2label or {}
        label = id2label.get(prediction_index)
        if label is None:
            label = id2label.get(str(prediction_index), str(prediction_index))

        return {
            "label": str(label),
            "confidence": confidence,
            "probabilities": {
                str(id2label.get(index, id2label.get(str(index), index))): float(probabilities[index].item())
                for index in range(probabilities.shape[0])
            },
        }


_CACHE: dict[str, LocalTextClassifier] = {}
_LOCK = threading.Lock()


def get_classifier(model_dir: Path) -> LocalTextClassifier:
    cache_key = str(model_dir.resolve())
    with _LOCK:
        if cache_key not in _CACHE:
            _CACHE[cache_key] = LocalTextClassifier(model_dir)
        return _CACHE[cache_key]
