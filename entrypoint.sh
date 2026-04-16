#!/bin/sh
# Entrypoint: ensure model is present, then start the Wyoming TTS server.
set -e

MODEL_DIR="${MODEL_DIR:-/model}"
URI="${WYOMING_URI:-tcp://0.0.0.0:10300}"
VOICE_NAME="${VOICE_NAME:-vits-cantonese}"
LANGUAGE="${LANGUAGE:-yue}"
SPEAKER_ID="${SPEAKER_ID:-0}"
SPEED="${SPEED:-1.0}"
NUM_THREADS="${NUM_THREADS:-2}"
PROVIDER="${PROVIDER:-cpu}"
DEBUG="${DEBUG:-}"

# Download model if not already present
python3 /app/download_model.py

# Build extra flags
EXTRA_FLAGS=""
if [ -n "$DEBUG" ]; then
    EXTRA_FLAGS="--debug"
fi

exec python3 /app/server.py \
    --uri "$URI" \
    --model-dir "$MODEL_DIR" \
    --voice-name "$VOICE_NAME" \
    --language "$LANGUAGE" \
    --speaker-id "$SPEAKER_ID" \
    --speed "$SPEED" \
    --num-threads "$NUM_THREADS" \
    --provider "$PROVIDER" \
    $EXTRA_FLAGS
