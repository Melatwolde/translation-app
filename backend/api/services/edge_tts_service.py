from __future__ import annotations

import io
import sys

import edge_tts


async def get_free_chinese_tts_pcm16(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural")
    mp3_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_bytes.extend(chunk["data"])

    import audioop

    sys.modules.setdefault("pyaudioop", audioop)
    from pydub import AudioSegment

    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    return audio.raw_data