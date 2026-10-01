# AGENTS.md - Translation Engine & Real-Time Audio Service

You are a senior full-stack and real-time audio systems engineer. Build only what is explicitly requested. Do not invent unapproved features, endpoints, or third-party libraries. Deliver production-ready, strictly typed, clean code with zero boilerplate fluff.

---

## 1. Project Overview & Architecture
Real-time phone call translation service supporting bidirectional audio and text:
- **Amharic / Afaan Oromo (`am`, `om`)** ↔ **Chinese / English (`zh`, `en`)**

### Hybrid AI Pipeline Architecture
- **`am`/`om` → `zh`/`en`:** Addis AI STT → Gemini Translation → Gemini TTS
- **`zh`/`en` → `am`/`om`:** Gemini STT → Gemini/Addis Translation → Addis AI TTS

### Infrastructure Stack
- **API Server:** FastAPI (Python 3.11+) with Uvicorn
- **Primary Database:** Supabase (PostgreSQL) via `supabase-py`
- **Cache & Ephemeral Memory:** Upstash Redis (`redis-py`) for:
  - Phone OTP verification (5-minute TTL)
  - Per-user rate limiting
  - Sliding-window context memory (last 6 conversation turns: `session:{session_id}:context`)
- **Real-Time Audio Transport:** LiveKit (`livekit-api`, `livekit`) + FastAPI WebSocket (`/ws/sessions/{session_id}`) with energy-based Voice Activity Detection (VAD) on PCM16 16kHz mono audio.
- **Client App:** Flutter 3.x (`apps/mobile`) using standard `http` package.

---

## 2. Monorepo Directory Layout

```text
translation-app/
├── AGENTS.md
├── .env.example
├── README.md
├── apps/
│   └── mobile/
│       ├── pubspec.yaml
│       ├── test/
│       │   └── widget_test.dart
│       └── lib/
│           ├── main.dart
│           ├── core/
│           │   ├── constants.dart
│           │   └── theme.dart
│           └── features/
│               └── translation/
│                   ├── data/
│                   │   └── api_service.dart
│                   └── presentation/
│                       └── screens/
│                           └── home_screen.dart
└── backend/api/
    ├── requirements.txt
    ├── schema.sql
    ├── config.py
    ├── database.py
    ├── redis_client.py
    ├── dependencies.py
    ├── main.py
    ├── models/
    │   ├── auth.py
    │   ├── user.py
    │   └── session.py
    ├── routers/
    │   ├── auth.py
    │   ├── users.py
    │   ├── sessions.py
    │   └── realtime.py
    ├── services/
    │   ├── auth_service.py
    │   ├── session_service.py
    │   ├── addis_service.py
    │   ├── gemini_service.py
    │   ├── translation_pipeline.py
    │   ├── livekit_service.py
    │   └── realtime_orchestrator.py
    └── tests/
        ├── conftest.py
        ├── test_health.py
        ├── test_auth.py
        ├── test_sessions.py
        ├── test_addis_service.py
        ├── test_gemini_service.py
        ├── test_translation_pipeline.py
        ├── test_process_audio_endpoint.py
        ├── test_livekit_service.py
        └── test_realtime_ws.py