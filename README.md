# AfroSino Voice Bridge: Bidirectional Amharic-Chinese Audio Translator

A high-performance, cost-optimized, real-time bidirectional speech translation pipeline designed to bridge low-resource languages (Amharic/Oromo) with high-demand economic languages (Mandarin Chinese). 

Built for cross-border trade, diplomacy, and real-time communication.

##  The Problem
Real-time voice translation for low-resource languages (like Amharic) typically relies entirely on expensive, high-latency cloud APIs for Speech-to-Text (STT), Machine Translation (MT), and Text-to-Speech (TTS). This results in high marginal costs per minute and poor latency for real-time duplex conversations.

##  The Solution & Architecture
We engineered a **hybrid, cost-optimized pipeline** that strategically routes audio through local AI models and zero-cost APIs to drive the marginal cost of translation to near zero, without sacrificing quality.

### Track 1: Chinese Speaker ➔ Amharic Listener
*Optimized for zero cloud STT costs.*
1. **STT (Local):** `faster-whisper` (Base model) runs locally to transcribe Chinese audio. (0 API cost, ultra-low latency).
2. **MT (Cloud):** Google Gemini translates Chinese text to Amharic.
3. **TTS (Cloud):** Addis AI generates native Amharic neural speech.

### Track 2: Amharic Speaker ➔ Chinese Listener
*Optimized for zero TTS costs.*
1. **STT (Cloud):** Addis AI transcribes Amharic audio to text.
2. **MT (Cloud):** Google Gemini translates Amharic text to Chinese.
3. **TTS (Local/Free):** Microsoft Edge-TTS generates high-fidelity Chinese neural speech. (0 API cost).

##  Key Features
- **Real-Time Duplex Capabilities:** Features a `DuplexTranslationSession` with per-listener echo suppression and rolling context windows, making it ready for live, two-way voice calls.
- **Extreme Cost Efficiency:** By leveraging local Whisper STT and Edge-TTS, we eliminate 50% of the cloud API calls, making the unit economics highly scalable for B2B SaaS.
- **Resilient & Async:** Built entirely on Python `asyncio` with exponential backoff, retry logic, and configurable timeouts to handle API rate limits and network spikes gracefully.
- **Standardized Audio Contract:** All internal audio is normalized to strict `PCM16 16kHz mono` bytes, ensuring seamless interoperability between WebSockets, local models, and cloud APIs.

##  Tech Stack
- **Core:** Python 3.11+, `asyncio`, `Pydantic` (Settings management)
- **Local AI:** `faster-whisper` (CTranslate2 optimized)
- **Cloud APIs:** Google Gemini (Translation), Addis AI (Amharic STT/TTS)
- **Free TTS:** `edge-tts` (Microsoft Edge Neural Voices)
- **Audio Processing:** `pydub`, `ffmpeg`, `audioop`

##  Installation & Setup

### Prerequisites
- Python 3.11+
- `ffmpeg` installed on your system (`sudo apt install ffmpeg` or `brew install ffmpeg`)

### 1. Clone and Install
```bash
git clone <your-repo-url>
cd translation-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt