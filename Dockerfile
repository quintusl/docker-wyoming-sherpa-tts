FROM python:3.11-slim

LABEL org.opencontainers.image.title="wyoming-sherpa-tts-cantonese" \
      org.opencontainers.image.description="Wyoming TTS server using sherpa-onnx with a Cantonese VITS model" \
      org.opencontainers.image.source="https://github.com/k2-fsa/sherpa-onnx"

# System dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip install --no-cache-dir \
        sherpa-onnx \
        wyoming \
        numpy \
        huggingface_hub

# Application files
WORKDIR /app
COPY server.py download_model.py entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

# Model is downloaded at first startup into /model (persisted via volume mount)
VOLUME ["/model"]

# Wyoming protocol default port
EXPOSE 10300

# Environment variable defaults (all overridable at runtime)
ENV MODEL_DIR=/model \
    WYOMING_URI=tcp://0.0.0.0:10300 \
    VOICE_NAME=vits-cantonese \
    LANGUAGE=yue \
    SPEAKER_ID=0 \
    SPEED=1.0 \
    NUM_THREADS=2 \
    PROVIDER=cpu

ENTRYPOINT ["/app/entrypoint.sh"]
