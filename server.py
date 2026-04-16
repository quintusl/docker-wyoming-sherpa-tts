#!/usr/bin/env python3
"""Wyoming TTS server backed by sherpa-onnx (Cantonese VITS model)."""

import argparse
import asyncio
import logging
import math
import signal
from functools import partial
from pathlib import Path
from typing import Optional

import numpy as np
import sherpa_onnx

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize

_LOGGER = logging.getLogger(__name__)

# Shared TTS instance (loaded once, reused across connections)
_TTS: Optional[sherpa_onnx.OfflineTts] = None


class SherpaOnnxTtsHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        *handler_args,
        **handler_kwargs,
    ) -> None:
        super().__init__(*handler_args, **handler_kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self.cli_args = cli_args

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if not Synthesize.is_type(event.type):
            return True

        synthesize = Synthesize.from_event(event)
        raw_text = synthesize.text
        text = " ".join(raw_text.strip().splitlines())

        _LOGGER.info("Synthesizing: %s", text)

        try:
            assert _TTS is not None, "TTS engine is not initialised"

            gen_config = sherpa_onnx.GenerationConfig()
            gen_config.sid = self.cli_args.speaker_id
            gen_config.speed = self.cli_args.speed
            audio = _TTS.generate(text, gen_config)

            if len(audio.samples) == 0:
                _LOGGER.error("sherpa-onnx returned no audio for input: %s", text)
                return True

            # Convert float32 [-1, 1] → int16 PCM bytes
            samples = np.array(audio.samples, dtype=np.float32)
            pcm_bytes = (samples * 32767).astype(np.int16).tobytes()

            rate = audio.sample_rate
            width = 2   # 16-bit
            channels = 1

            await self.write_event(
                AudioStart(rate=rate, width=width, channels=channels).event()
            )

            chunk_bytes = self.cli_args.samples_per_chunk * width * channels
            num_chunks = max(1, math.ceil(len(pcm_bytes) / chunk_bytes))
            for i in range(num_chunks):
                offset = i * chunk_bytes
                await self.write_event(
                    AudioChunk(
                        audio=pcm_bytes[offset : offset + chunk_bytes],
                        rate=rate,
                        width=width,
                        channels=channels,
                    ).event()
                )

            await self.write_event(AudioStop().event())
            _LOGGER.info("Done synthesizing")

        except Exception:
            _LOGGER.exception("Error during synthesis")

        return True


def build_tts(args: argparse.Namespace) -> sherpa_onnx.OfflineTts:
    model_dir = Path(args.model_dir)
    onnx_files = list(model_dir.glob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(f"No .onnx file found in {model_dir}")
    model_file = onnx_files[0]

    lexicon_file = model_dir / "lexicon.txt"
    tokens_file = model_dir / "tokens.txt"
    rule_fst_file = model_dir / "rule.fst"

    tts_config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(model_file),
                lexicon=str(lexicon_file) if lexicon_file.exists() else "",
                tokens=str(tokens_file) if tokens_file.exists() else "",
            ),
            provider=args.provider,
            debug=args.debug,
            num_threads=args.num_threads,
        ),
        rule_fsts=str(rule_fst_file) if rule_fst_file.exists() else "",
    )

    if not tts_config.validate():
        raise ValueError(
            "Invalid TTS config – check that all required model files are present."
        )

    _LOGGER.info("Loading TTS model from %s", model_dir)
    tts = sherpa_onnx.OfflineTts(tts_config)
    _LOGGER.info("TTS model loaded (sample_rate=%d)", tts.sample_rate)
    return tts


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wyoming TTS server using sherpa-onnx"
    )
    parser.add_argument(
        "--uri",
        default="tcp://0.0.0.0:10300",
        help="Server URI (default: tcp://0.0.0.0:10300)",
    )
    parser.add_argument(
        "--model-dir",
        required=True,
        help="Directory containing the VITS ONNX model and supporting files",
    )
    parser.add_argument(
        "--voice-name",
        default="vits-cantonese",
        help="Voice name reported to Home Assistant (default: vits-cantonese)",
    )
    parser.add_argument(
        "--language",
        default="yue-HK",
        help="BCP-47 language tag (default: yue for Cantonese)",
    )
    parser.add_argument(
        "--speaker-id",
        type=int,
        default=0,
        help="Speaker ID for multi-speaker models (default: 0)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--samples-per-chunk",
        type=int,
        default=1024,
        help="Audio samples per Wyoming chunk (default: 1024)",
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=2,
        help="ONNX inference threads (default: 2)",
    )
    parser.add_argument(
        "--provider",
        default="cpu",
        help="ONNX provider: cpu | cuda | coreml (default: cpu)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    global _TTS
    _TTS = build_tts(args)

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="sherpa-tts",
                description="sherpa-onnx offline TTS (Cantonese VITS)",
                version="1.0.0",
                attribution=Attribution(
                    name="k2-fsa / csukuangfj",
                    url="https://github.com/k2-fsa/sherpa-onnx",
                ),
                installed=True,
                voices=[
                    TtsVoice(
                        name=args.voice_name,
                        description="Cantonese VITS",
                        attribution=Attribution(
                            name="csukuangfj",
                            url="https://huggingface.co/csukuangfj/vits-melo-tts-zh_en",
                        ),
                        installed=True,
                        languages=[args.language],
                        version="1.0",
                    )
                ],
            )
        ]
    )

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Wyoming sherpa-onnx TTS server ready on %s", args.uri)

    server_task = asyncio.create_task(
        server.run(partial(SherpaOnnxTtsHandler, wyoming_info, args))
    )

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, server_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, server_task.cancel)

    try:
        await server_task
    except asyncio.CancelledError:
        _LOGGER.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
