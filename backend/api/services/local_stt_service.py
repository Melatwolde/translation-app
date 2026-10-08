import numpy as np
from faster_whisper import WhisperModel

class LocalChineseSTTService:
    def __init__(self):
        # "base" is the perfect balance of speed and accuracy for Chinese.
        # It loads quickly and runs well on standard CPUs.
        self.model = WhisperModel("base", device="cpu", compute_type="int8")

    def transcribe_sync(self, pcm16_bytes: bytes) -> str:
        # 1. Convert raw PCM16 bytes to a numpy float32 array (required by faster-whisper)
        # We divide by 32768.0 to normalize the audio to the -1.0 to 1.0 range
        audio_array = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        # 2. Transcribe, forcing the language to Chinese ("zh")
        segments, info = self.model.transcribe(audio_array, language="zh", beam_size=5)
        
        # 3. Combine all text segments into a single string
        return " ".join(segment.text for segment in segments).strip()
