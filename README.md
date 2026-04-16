# wyoming-sherpa-tts-cantonese

A Docker image that runs a **Wyoming TTS server** backed by [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), using the Cantonese VITS model [`csukuangfj/vits-melo-tts-zh_en`](https://huggingface.co/csukuangfj/vits-melo-tts-zh_en) from HuggingFace.

The [Wyoming protocol](https://github.com/rhasspy/wyoming) is natively supported by Home Assistant's [Wyoming integration](https://www.home-assistant.io/integrations/wyoming).

---

## Quick start

```bash
# Build
docker build -t wyoming-sherpa-tts-cantonese .

# Run (model is downloaded from HuggingFace on first start, ~114 MB)
docker run -d \
  --name wyoming-sherpa-tts \
  -p 10300:10300 \
  -v sherpa-tts-model:/model \
  wyoming-sherpa-tts-cantonese
```

On first start the container downloads the Cantonese model from HuggingFace into the `/model` volume. Subsequent starts reuse the cached model.

---

## Home Assistant setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Wyoming Protocol**.
3. Enter:
   - **Host**: IP address of the machine running Docker
   - **Port**: `10300`
4. A TTS entity named **vits-cantonese** will appear in the `yue` language.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_DIR` | `/model` | Directory where model files are stored |
| `WYOMING_URI` | `tcp://0.0.0.0:10300` | Bind address for the Wyoming server |
| `VOICE_NAME` | `vits-cantonese` | Voice name shown in Home Assistant |
| `LANGUAGE` | `yue` | BCP-47 language tag (Cantonese) |
| `SPEAKER_ID` | `0` | Speaker ID (single-speaker model, keep at 0) |
| `SPEED` | `1.0` | Synthesis speed (>1 = faster, <1 = slower) |
| `NUM_THREADS` | `2` | ONNX inference threads |
| `PROVIDER` | `cpu` | ONNX execution provider (`cpu`, `cuda`, `coreml`) |
| `DEBUG` | _(unset)_ | Set to any non-empty value to enable debug logs |
| `HF_TOKEN` | _(unset)_ | HuggingFace token (not required for this public model) |

---

## Model

| Item | Detail |
|---|---|
| HuggingFace repo | [`csukuangfj/vits-melo-tts-zh_en`](https://huggingface.co/csukuangfj/vits-melo-tts-zh_en) |
| Architecture | VITS (single speaker) |
| Language | Cantonese (yue) |
| Sample rate | 22 050 Hz |
| ONNX file size | ~114 MB |

---

## Custom model

Mount a different VITS model directory and set `MODEL_DIR` to point at it:

```bash
docker run -d \
  --name wyoming-sherpa-tts \
  -p 10300:10300 \
  -v /path/to/my-model:/custom-model \
  -e MODEL_DIR=/custom-model \
  -e VOICE_NAME=my-voice \
  -e LANGUAGE=zh \
  wyoming-sherpa-tts-cantonese
```

The directory must contain at minimum:
- `*.onnx` — VITS model file
- `tokens.txt` — phoneme token list
- `lexicon.txt` — word-to-phoneme lexicon (if the model requires it)
- `rule.fst` — text-normalisation rules (optional)
