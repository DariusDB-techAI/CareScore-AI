"""Tải PhoBERT về local — chỉ file PyTorch cần cho train, hỗ trợ resume."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "600")

from huggingface_hub import hf_hub_download

REPO_ID = "vinai/phobert-base"
LOCAL_DIR = Path("models/phobert-base")
HF_CACHE = Path.home() / ".cache/huggingface/hub"

REQUIRED_FILES = [
    "config.json",
    "vocab.txt",
    "bpe.codes",
    "tokenizer.json",
    "pytorch_model.bin",
]

MIN_WEIGHT_BYTES = 500_000_000  # ~500MB

# Thử lần lượt nếu mạng lỗi (hf-mirror thường ổn hơn ở VN)
ENDPOINTS = [
    os.environ.get("HF_ENDPOINT", "").rstrip("/"),
    "https://hf-mirror.com",
    "https://huggingface.co",
]
ENDPOINTS = [e for e in ENDPOINTS if e]  # bỏ chuỗi rỗng, giữ thứ tự unique
_seen = set()
ENDPOINTS = [e for e in ENDPOINTS if not (e in _seen or _seen.add(e))]


def find_cached_weight() -> Path | None:
    """Tìm pytorch_model.bin đã tải dở/xong trong HF cache."""
    repo_cache = HF_CACHE / f"models--{REPO_ID.replace('/', '--')}"

    # 1) Symlink trong snapshots/
    for snap in (repo_cache / "snapshots").glob("*/pytorch_model.bin"):
        blob = snap.resolve()
        if blob.is_file() and blob.stat().st_size >= MIN_WEIGHT_BYTES:
            return blob

    # 2) Blob hoàn chỉnh (không có .incomplete)
    blobs_dir = repo_cache / "blobs"
    if blobs_dir.is_dir():
        for blob in blobs_dir.iterdir():
            if blob.is_file() and not blob.name.endswith(".incomplete"):
                if blob.stat().st_size >= MIN_WEIGHT_BYTES:
                    return blob

    return None


def copy_from_cache(dest: Path) -> bool:
    cached = find_cached_weight()
    if cached is None:
        return False
    print(f"✓ Tìm thấy trong HF cache ({cached.stat().st_size / 1e6:.0f} MB)")
    print(f"  → copy sang {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached, dest)
    return dest.stat().st_size >= MIN_WEIGHT_BYTES


def download_with_curl(filename: str, dest: Path, endpoint: str) -> bool:
    url = f"{endpoint}/{REPO_ID}/resolve/main/{filename}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  → curl [{endpoint}]: {filename}")
    result = subprocess.run(
        [
            "curl", "-L", "-C", "-",
            "--retry", "10", "--retry-delay", "5",
            "--connect-timeout", "30",
            "-o", str(dest), url,
        ],
        check=False,
    )
    return result.returncode == 0


def download_file(filename: str) -> Path:
    dest = LOCAL_DIR / filename

    if filename == "pytorch_model.bin":
        if dest.exists() and dest.stat().st_size >= MIN_WEIGHT_BYTES:
            print(f"✓ {filename} đã có ({dest.stat().st_size / 1e6:.0f} MB)")
            return dest
        if copy_from_cache(dest):
            print(f"✓ {filename} copy từ cache xong")
            return dest
    elif dest.exists() and dest.stat().st_size > 0:
        print(f"✓ {filename} đã có")
        return dest

    print(f"\nĐang tải {filename}...")

    if filename != "pytorch_model.bin":
        hf_hub_download(repo_id=REPO_ID, filename=filename, local_dir=str(LOCAL_DIR))
        return dest

    # pytorch_model.bin: thử từng mirror bằng curl (resume ổn định hơn)
    for endpoint in ENDPOINTS:
        print(f"  Thử endpoint: {endpoint}")
        os.environ["HF_ENDPOINT"] = endpoint
        try:
            hf_hub_download(repo_id=REPO_ID, filename=filename, local_dir=str(LOCAL_DIR))
            if dest.exists() and dest.stat().st_size >= MIN_WEIGHT_BYTES:
                return dest
        except Exception as e:
            print(f"  huggingface_hub lỗi: {e}")

        if download_with_curl(filename, dest, endpoint):
            if dest.stat().st_size >= MIN_WEIGHT_BYTES:
                return dest
            print(f"  Tải dở: {dest.stat().st_size / 1e6:.0f} MB — chạy lại script để resume")

    return dest


def convert_to_safetensors() -> Path:
    """Chuyển pytorch_model.bin → model.safetensors (torch<2.6 + transformers 5.x cần file này)."""
    import torch
    from safetensors.torch import save_file

    src = LOCAL_DIR / "pytorch_model.bin"
    dst = LOCAL_DIR / "model.safetensors"
    if dst.exists() and dst.stat().st_size > MIN_WEIGHT_BYTES:
        print(f"✓ model.safetensors đã có ({dst.stat().st_size / 1e6:.0f} MB)")
        return dst
    if not src.exists() or src.stat().st_size < MIN_WEIGHT_BYTES:
        return dst

    print("Đang chuyển pytorch_model.bin → model.safetensors...")
    state = torch.load(src, map_location="cpu", weights_only=False)
    save_file({k: v.clone() for k, v in state.items()}, dst)
    print(f"✓ model.safetensors: {dst.stat().st_size / 1e6:.0f} MB")
    return dst


def main() -> int:
    print(f"--- Tải {REPO_ID} -> {LOCAL_DIR} ---")
    print("HF_HUB_DISABLE_XET =", os.environ.get("HF_HUB_DISABLE_XET"))
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)

    for filename in REQUIRED_FILES:
        download_file(filename)

    weight = LOCAL_DIR / "pytorch_model.bin"
    safetensors = convert_to_safetensors()
    if safetensors.exists() and safetensors.stat().st_size >= MIN_WEIGHT_BYTES:
        print(f"\n[THÀNH CÔNG] Model sẵn sàng: {LOCAL_DIR.resolve()}")
        print(f"  model.safetensors: {safetensors.stat().st_size / 1e6:.0f} MB")
        return 0
    if weight.exists() and weight.stat().st_size >= MIN_WEIGHT_BYTES:
        print(f"\n[THÀNH CÔNG] Model sẵn sàng: {LOCAL_DIR.resolve()}")
        print(f"  pytorch_model.bin: {weight.stat().st_size / 1e6:.0f} MB")
        return 0

    print("\n[LỖI] Chưa có pytorch_model.bin đủ ~540 MB.")
    if weight.exists():
        print(f"  Hiện có: {weight.stat().st_size / 1e6:.0f} MB")
    print("\nThử:")
    print("  1. python download_model.py          (resume)")
    print("  2. Bật VPN rồi chạy lại")
    print("  3. Tải thủ công vào models/phobert-base/pytorch_model.bin")
    print("     https://huggingface.co/vinai/phobert-base/tree/main")
    return 1


if __name__ == "__main__":
    sys.exit(main())
