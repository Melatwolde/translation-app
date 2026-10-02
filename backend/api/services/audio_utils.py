"""Audio normalization for the translation pipeline.

AUDIO CONTRACT (mandatory):
- Format: 16-bit signed little-endian PCM
- Channels: Mono
- Sample Rate: 16000 Hz
- No other format is accepted by the translation pipeline
"""

from __future__ import annotations

import logging
import struct
import wave
from io import BytesIO

LOGGER = logging.getLogger(__name__)
PCM16_SAMPLE_RATE = 16_000


class AudioFormatError(ValueError):
    """An audio payload cannot be converted to the translation audio contract."""

    status_code = 422


def is_valid_pcm16_16k_mono(data: bytes) -> bool:
    """Return whether *data* is a non-empty raw PCM16 contract payload.

    Raw PCM has no header, so its sample rate and channel count cannot be
    inferred from bytes alone. Callers of this function assert those two
    properties through the mandatory transport contract; this function checks
    the representation that can be verified locally.
    """
    return bool(data) and len(data) % 2 == 0 and not data.startswith(b"RIFF")


def ensure_pcm16_16k_mono(audio: bytes, original_sample_rate: int | None = None) -> bytes:
    """Return raw 16 kHz mono little-endian PCM16, converting WAV when needed."""
    if not audio:
        raise AudioFormatError("Audio payload is empty")

    if audio.startswith(b"RIFF"):
        return _normalize_wav(audio)

    if len(audio) % 2:
        raise AudioFormatError("Raw PCM16 audio must contain complete 16-bit samples")

    if original_sample_rate is None or original_sample_rate == PCM16_SAMPLE_RATE:
        return audio
    if original_sample_rate <= 0:
        raise AudioFormatError("original_sample_rate must be a positive integer")

    LOGGER.warning(
        "Resampling raw PCM16 mono audio from %d Hz to %d Hz",
        original_sample_rate,
        PCM16_SAMPLE_RATE,
    )
    return _resample_pcm16_mono(audio, original_sample_rate)


def _normalize_wav(audio: bytes) -> bytes:
    try:
        with wave.open(BytesIO(audio), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            compression = wav.getcomptype()
            frames = wav.readframes(wav.getnframes())
    except (EOFError, wave.Error) as error:
        raise AudioFormatError("Audio is not a readable PCM WAV file") from error

    if compression != "NONE":
        raise AudioFormatError("Only uncompressed PCM WAV audio can be converted")
    if channels < 1 or sample_width not in {1, 2, 3, 4} or sample_rate <= 0:
        raise AudioFormatError("WAV audio has unsupported channel, sample width, or sample rate")

    pcm16 = _to_pcm16_mono(frames, sample_width, channels)
    if sample_rate != PCM16_SAMPLE_RATE:
        pcm16 = _resample_pcm16_mono(pcm16, sample_rate)

    LOGGER.warning(
        "Normalized WAV audio to PCM16 mono at %d Hz (source: %d Hz, %d channel(s), %d-bit)",
        PCM16_SAMPLE_RATE,
        sample_rate,
        channels,
        sample_width * 8,
    )
    return pcm16


def _to_pcm16_mono(frames: bytes, sample_width: int, channels: int) -> bytes:
    frame_size = sample_width * channels
    if len(frames) % frame_size:
        raise AudioFormatError("WAV audio contains an incomplete frame")

    output = bytearray(len(frames) // frame_size * 2)
    output_index = 0
    for frame_offset in range(0, len(frames), frame_size):
        samples = [
            _pcm_sample_to_int16(frames, frame_offset + channel * sample_width, sample_width)
            for channel in range(channels)
        ]
        struct.pack_into("<h", output, output_index, sum(samples) // channels)
        output_index += 2
    return bytes(output)


def _pcm_sample_to_int16(data: bytes, offset: int, sample_width: int) -> int:
    sample = data[offset : offset + sample_width]
    if sample_width == 1:
        return (sample[0] - 128) << 8
    value = int.from_bytes(sample, byteorder="little", signed=True)
    return value >> (8 * (sample_width - 2)) if sample_width > 2 else value


def _resample_pcm16_mono(audio: bytes, source_sample_rate: int) -> bytes:
    if source_sample_rate <= 0:
        raise AudioFormatError("original_sample_rate must be a positive integer")
    if source_sample_rate == PCM16_SAMPLE_RATE:
        return audio

    source_count = len(audio) // 2
    target_count = max(1, round(source_count * PCM16_SAMPLE_RATE / source_sample_rate))
    output = bytearray(target_count * 2)
    for target_index in range(target_count):
        source_position = target_index * source_sample_rate
        lower_index = min(source_position // PCM16_SAMPLE_RATE, source_count - 1)
        upper_index = min(lower_index + 1, source_count - 1)
        fraction = source_position % PCM16_SAMPLE_RATE
        lower = struct.unpack_from("<h", audio, lower_index * 2)[0]
        upper = struct.unpack_from("<h", audio, upper_index * 2)[0]
        sample = lower + (upper - lower) * fraction // PCM16_SAMPLE_RATE
        struct.pack_into("<h", output, target_index * 2, sample)
    return bytes(output)
