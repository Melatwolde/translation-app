from __future__ import annotations

import io
import struct
import wave

import pytest

from services.audio_utils import AudioFormatError, ensure_pcm16_16k_mono, is_valid_pcm16_16k_mono


def test_valid_raw_pcm16_contract_payload_is_unchanged() -> None:
    audio = struct.pack("<3h", -10, 0, 10)
    assert is_valid_pcm16_16k_mono(audio)
    assert ensure_pcm16_16k_mono(audio) == audio


def test_resamples_raw_pcm16_when_source_rate_is_supplied() -> None:
    audio = struct.pack("<4h", -100, 0, 100, 200)
    converted = ensure_pcm16_16k_mono(audio, original_sample_rate=8_000)
    assert len(converted) == 16
    assert is_valid_pcm16_16k_mono(converted)


def test_converts_stereo_wav_to_pcm16_mono_16k() -> None:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(8_000)
        wav.writeframes(struct.pack("<4h", 100, 300, 200, 400))

    converted = ensure_pcm16_16k_mono(buffer.getvalue())
    assert converted == struct.pack("<4h", 200, 250, 300, 300)


def test_rejects_incomplete_raw_pcm16_sample() -> None:
    with pytest.raises(AudioFormatError, match="complete 16-bit"):
        ensure_pcm16_16k_mono(b"\x00")
