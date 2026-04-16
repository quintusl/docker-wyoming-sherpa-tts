#!/usr/bin/env python3
"""Download the Cantonese VITS model from HuggingFace into /model."""

import os
import sys
from pathlib import Path

MODEL_DIR = Path("/model")
REPO_ID = "csukuangfj/vits-melo-tts-zh_en"
FILES = [
    "model.onnx",
    "lexicon.txt",
    "tokens.txt",
    "rule.fst",
    "config.json",
]


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded (skip if the ONNX file is present)
    onnx_path = MODEL_DIR / "model.onnx"
    if onnx_path.exists() and onnx_path.stat().st_size > 1_000_000:
        print(f"Model already present at {MODEL_DIR}, skipping download.")
        return

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("huggingface_hub not installed; cannot download model.", file=sys.stderr)
        sys.exit(1)

    hf_token = os.environ.get("HF_TOKEN")  # optional, for gated repos

    for filename in FILES:
        dest = MODEL_DIR / filename
        if dest.exists():
            print(f"  {filename} already exists, skipping.")
            continue
        print(f"  Downloading {filename} …", flush=True)
        local = hf_hub_download(
            repo_id=REPO_ID,
            filename=filename,
            token=hf_token,
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False,
        )
        print(f"  Saved to {local}")

    print("Download complete.")


if __name__ == "__main__":
    main()
