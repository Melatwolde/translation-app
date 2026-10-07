from __future__ import annotations

from services.alibaba_service import split_frame


def test_split_frame_keeps_binary_audio_out_of_json_parser() -> None:
    assert split_frame(b"\x00\xff")[0] == "audio"
    kind, payload = split_frame('{"event":"task-started"}')
    assert kind == "json"
    assert payload == {"event": "task-started"}
