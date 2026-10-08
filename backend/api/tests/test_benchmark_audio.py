from __future__ import annotations

import importlib.util
import wave
from pathlib import Path
from types import SimpleNamespace


def test_benchmark_wav_writer_saves_pcm16_audio(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_amharic_audio.py"
    spec = importlib.util.spec_from_file_location("benchmark_amharic_audio", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "result_zh.wav"
    module._write_pcm16_wav(output, b"\x00\x00\x01\x00")
    with wave.open(str(output), "rb") as saved:
        assert (saved.getnchannels(), saved.getsampwidth(), saved.getframerate()) == (1, 2, 16_000)
        assert saved.readframes(2) == b"\x00\x00\x01\x00"


def test_chinese_benchmark_does_not_require_alibaba_credentials() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_amharic_audio.py"
    spec = importlib.util.spec_from_file_location("benchmark_amharic_audio", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pipeline = SimpleNamespace(
        addis=SimpleNamespace(settings=SimpleNamespace(addis_ai_api_key="addis-key", addis_ai_base_url="https://addis")),
        translator=SimpleNamespace(settings=SimpleNamespace(translation_provider="gemini", gemini_api_key="gemini-key")),
    )

    module._require_provider_keys(pipeline, "am", "zh")
