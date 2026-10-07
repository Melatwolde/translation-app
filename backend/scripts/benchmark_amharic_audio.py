"""Run the production translation pipeline over a directory of WAV fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import wave
from pathlib import Path
from time import perf_counter

API_ROOT = Path(__file__).resolve().parents[1] / "api"
sys.path.insert(0, str(API_ROOT))

from services.audio_utils import ensure_pcm16_16k_mono  # noqa: E402
from services.translation_pipeline import TranslationPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("test_amh"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--source-language", default="am")
    parser.add_argument("--target-language", default="en")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and normalize every input without calling external AI providers.",
    )
    return parser.parse_args()


def output_text(record: dict[str, object]) -> str:
    return "\n".join(
        (
            f"Input: {record['file']}",
            f"Languages: {record['source_language']} -> {record['target_language']}",
            f"Audio duration: {record['audio_duration_seconds']:.3f} s",
            f"Pipeline latency: {record.get('pipeline_latency_ms', 'not measured')} ms",
            f"Result status: {record['result_status']}",
            "",
            "Source transcript:",
            str(record['source_text']),
            "",
            "Translation:",
            str(record['translated_text']),
            "",
        )
    )


async def benchmark(args: argparse.Namespace) -> list[dict[str, object]]:
    wav_files = sorted(args.input_dir.glob("*.wav"))
    if not wav_files:
        raise SystemExit(f"No WAV files found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = TranslationPipeline()
    if not args.validate_only:
        _require_provider_keys(pipeline, args.source_language, args.target_language)
    records: list[dict[str, object]] = []

    for wav_file in wav_files:
        started = perf_counter()
        try:
            normalized = ensure_pcm16_16k_mono(wav_file.read_bytes())
            normalized_ms = round((perf_counter() - started) * 1000)
            if args.validate_only:
                record = {
                    "file": wav_file.name,
                    "source_language": args.source_language,
                    "target_language": args.target_language,
                    "audio_duration_seconds": round(len(normalized) / 32_000, 3),
                    "normalized_audio_bytes": len(normalized),
                    "normalization_latency_ms": normalized_ms,
                    "source_text": "No transcript produced.",
                    "translated_text": "No translation produced.",
                    "result_status": "blocked-provider-not-run",
                }
                (args.output_dir / f"{wav_file.stem}.translation.txt").write_text(
                    output_text(record), encoding="utf-8"
                )
                records.append(record)
                continue
            result = await pipeline.translate_audio(normalized, args.source_language, args.target_language)
            elapsed_ms = round((perf_counter() - started) * 1000)

            if result.audio:
                _write_pcm16_wav(args.output_dir / f"{wav_file.stem}_{args.target_language}.wav", result.audio)
            record: dict[str, object] = {
                "file": wav_file.name,
                "source_language": args.source_language,
                "target_language": args.target_language,
                "audio_duration_seconds": round(len(normalized) / 32_000, 3),
                "normalized_audio_bytes": len(normalized),
                "normalization_latency_ms": normalized_ms,
                "pipeline_latency_ms": result.latency_ms,
                "observed_wall_latency_ms": elapsed_ms,
                "source_text": result.source_text,
                "translated_text": result.translated_text,
                "output_audio_bytes": len(result.audio),
                "provider_path": result.provider_path,
                "result_status": "completed" if result.audio else "completed-text-only-no-english-tts",
            }
            (args.output_dir / f"{wav_file.stem}.translation.txt").write_text(
                output_text(record), encoding="utf-8"
            )
        except Exception as error:  # Keep the report useful if one provider call fails.
            record = {
                "file": wav_file.name,
                "source_language": args.source_language,
                "target_language": args.target_language,
                "result_status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
            (args.output_dir / f"{wav_file.stem}.translation.txt").write_text(
                output_text({**record, "audio_duration_seconds": 0, "source_text": "", "translated_text": ""}),
                encoding="utf-8",
            )
        records.append(record)
    return records


def _require_provider_keys(pipeline: TranslationPipeline, source: str, target: str) -> None:
    """Fail before processing fixtures when a required production credential is absent."""
    source, target = source.lower(), target.lower()
    settings = pipeline.translator.settings
    missing: list[str] = []
    if source in {"am", "om"} or target in {"am", "om"}:
        if not pipeline.addis.settings.addis_ai_api_key:
            missing.append("ADDIS_AI_API_KEY (or ADDIS_API_KEY)")
        if not pipeline.addis.settings.addis_ai_base_url:
            missing.append("ADDIS_AI_BASE_URL")
    if source in {"zh", "zh-cn", "chinese"} or target in {"zh", "zh-cn", "chinese"}:
        if not pipeline.alibaba.settings.alibaba_dashscope_api_key:
            missing.append("ALIBABA_DASHSCOPE_API_KEY")
    if settings.translation_provider != "gemini":
        missing.append("TRANSLATION_PROVIDER=gemini")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if missing:
        raise SystemExit("Missing required provider configuration: " + ", ".join(missing))


def _write_pcm16_wav(path: Path, pcm16: bytes) -> None:
    """Write the pipeline's 16 kHz mono PCM16 contract as a valid WAV file."""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(pcm16)


def write_report(output_dir: Path, records: list[dict[str, object]]) -> None:
    completed = [record for record in records if "pipeline_latency_ms" in record]
    valid = [record for record in completed if record["result_status"] == "completed"]
    blocked = [record for record in records if record["result_status"] == "blocked-provider-not-run"]
    failed = [record for record in records if record["result_status"] == "failed"]
    latencies = [int(record["pipeline_latency_ms"]) for record in completed]
    lines = [
        "# Amharic Translation Latency Report",
        "",
        f"Test direction: `{records[0]['source_language']} -> {records[0]['target_language']}`." if records else "Test direction: none.",
        f"Files discovered: {len(records)}.",
        f"Pipeline calls completed: {len(completed)}.",
        f"Real transcription results: {len(valid)}.",
        f"Provider failures: {len(failed)}.",
        "",
    ]
    if latencies:
        lines.extend(
            (
                f"Mean reported pipeline latency: {sum(latencies) / len(latencies):.0f} ms.",
                f"Minimum/maximum reported pipeline latency: {min(latencies)} / {max(latencies)} ms.",
                "",
            )
        )
    if blocked:
        lines.extend(
            (
                "## Provider status",
                "",
                "Provider calls were skipped because the benchmark ran with `--validate-only`.",
                "",
            )
        )
    if failed:
        lines.extend(("## Provider errors", ""))
        for record in failed:
            lines.append(
                f"- {record['file']}: {record.get('error_type', 'Error')}: "
                f"{record.get('error', 'No error detail recorded')}"
            )
        lines.append("")
    text_only = [record for record in completed if record["result_status"] == "completed-text-only-no-english-tts"]
    if text_only:
        lines.extend(
            (
                "## Validity warning",
                "",
                "English is configured as a temporary text-only target; those rows have no synthesized audio.",
                "",
            )
        )
    lines.extend(("## Per-file results", "", "| File | Audio s | Pipeline ms | Status | Error |", "| --- | ---: | ---: | --- | --- |"))
    for record in records:
        lines.append(
            "| {file} | {duration} | {latency} | {status} |".format(
                file=record["file"],
                duration=record.get("audio_duration_seconds", "-"),
                latency=record.get("pipeline_latency_ms", "-"),
                status=record["result_status"],
                error=record.get("error", "").replace("|", "\\|").replace("\n", " "),
            )
        )
    lines.append("")
    (output_dir / "translation_latency_report.md").write_text("\n".join(lines), encoding="utf-8")
    (output_dir / "translation_latency_report.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    records = asyncio.run(benchmark(args))
    write_report(args.output_dir, records)


if __name__ == "__main__":
    main()
