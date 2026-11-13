from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from .config import AgentConfig, default_macwhisper_bin
from .glossary import apply_glossary, load_glossary
from .local_clean import local_clean
from .naming import (
    build_final_filename,
    infer_date,
    infer_topic_from_path,
    infer_topic_with_openai,
    unique_path,
)
from .polisher import polish_with_openai
from .prompting import build_polish_prompt
from .transcriber import transcribe_with_macwhisper
from .terminology import correct_terms


MEDIA_EXTENSIONS = {
    ".aac",
    ".aif",
    ".aiff",
    ".flac",
    ".m4a",
    ".m4v",
    ".mov",
    ".mp3",
    ".mp4",
    ".wav",
    ".webm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tw-transcript",
        description="Local-first audio/video transcription agent for Traditional Chinese.",
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Audio/video file to transcribe, or a transcript when --input-is-transcript is used.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "--batch-dir",
        type=Path,
        help="Process every audio/video file in this folder.",
    )
    parser.add_argument(
        "--move-done",
        type=Path,
        help="Move source media here after successful batch processing.",
    )
    parser.add_argument("--backend", choices=["macwhisper"], default="macwhisper")
    parser.add_argument("--macwhisper-bin", default=default_macwhisper_bin())
    parser.add_argument("--model", dest="macwhisper_model", default=None)
    parser.add_argument("--polish", choices=["local", "openai"], default="local")
    parser.add_argument("--openai-model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--glossary", type=Path, default=Path("glossary.tsv"))
    parser.add_argument("--term-profile", choices=["shared", "lesson5", "lesson6", "lesson7", "lesson8"], default="shared",
                        help="Verified terminology; lesson profiles are only for the reviewed lessons.")
    parser.add_argument(
        "--input-is-transcript",
        action="store_true",
        help="Treat input as an existing raw transcript and skip MacWhisper.",
    )
    parser.add_argument(
        "--no-auto-name",
        action="store_true",
        help="Do not create a final YYYY-MM-DD-topic.md transcript file.",
    )
    return parser.parse_args()


def make_run_dir(out_dir: Path, input_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = input_path.stem.replace(" ", "-")
    run_dir = out_dir / f"{stem}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def iter_media_files(batch_dir: Path) -> list[Path]:
    if not batch_dir.exists():
        raise FileNotFoundError(batch_dir)
    return sorted(
        path
        for path in batch_dir.iterdir()
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    )


def naming_source_path(input_path: Path, *, input_is_transcript: bool) -> Path:
    if not input_is_transcript:
        return input_path

    metadata_path = input_path.parent / "metadata.json"
    if not metadata_path.exists():
        return input_path

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return input_path

    original = metadata.get("input_path")
    if isinstance(original, str) and original.strip():
        return Path(original)
    return input_path


def run(config: AgentConfig) -> Path:
    if not config.input_path.exists():
        raise FileNotFoundError(config.input_path)

    run_dir = make_run_dir(config.out_dir, config.input_path)
    glossary_pairs = load_glossary(config.glossary_path)

    if config.input_is_transcript:
        raw = config.input_path.read_text(encoding="utf-8")
    else:
        raw = transcribe_with_macwhisper(
            config.input_path,
            macwhisper_bin=config.macwhisper_bin,
            model=config.macwhisper_model,
        )
    raw_path = run_dir / "raw.txt"
    write_text(raw_path, raw)

    cleaned = local_clean(apply_glossary(raw, glossary_pairs))
    cleaned, term_changes = correct_terms(cleaned, config.term_profile)
    (run_dir / "term_corrections.json").write_text(
        json.dumps(term_changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cleaned_path = run_dir / "local_cleaned.txt"
    write_text(cleaned_path, cleaned)

    prompt = build_polish_prompt(
        cleaned,
        glossary_pairs,
        language_note=config.language_note,
    )
    prompt_path = run_dir / "openai_prompt.txt"
    write_text(prompt_path, prompt)

    if config.polish == "openai":
        polished = polish_with_openai(prompt, model=config.openai_model)
    else:
        polished = cleaned

    polished_path = run_dir / "polished.md"
    write_text(polished_path, polished)

    final_named_path = None
    final_date = None
    final_topic = None
    if config.auto_name:
        source_path = naming_source_path(
            config.input_path,
            input_is_transcript=config.input_is_transcript,
        )
        final_date = infer_date(source_path)
        final_topic = infer_topic_from_path(source_path)
        if config.polish == "openai":
            final_topic = infer_topic_with_openai(
                polished,
                model=config.openai_model,
                fallback=final_topic,
            )
        final_named_path = unique_path(run_dir / build_final_filename(final_date, final_topic))
        write_text(final_named_path, polished)

    metadata = {
        "input_path": str(config.input_path.resolve()),
        "backend": config.backend,
        "macwhisper_bin": config.macwhisper_bin,
        "macwhisper_model": config.macwhisper_model,
        "polish": config.polish,
        "input_is_transcript": config.input_is_transcript,
        "openai_model": config.openai_model if config.polish == "openai" else None,
        "glossary_path": str(config.glossary_path) if config.glossary_path else None,
        "term_profile": config.term_profile,
        "term_corrections": len(term_changes),
        "final_date": final_date,
        "final_topic": final_topic,
        "outputs": {
            "raw": str(raw_path),
            "local_cleaned": str(cleaned_path),
            "prompt": str(prompt_path),
            "polished": str(polished_path),
            "final_named": str(final_named_path) if final_named_path else None,
        },
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return run_dir


def run_batch(args: argparse.Namespace) -> Path:
    files = iter_media_files(args.batch_dir)
    batch_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_summary_path = args.out_dir / f"batch-{batch_stamp}.json"
    batch_summary_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for input_path in files:
        item = {
            "input_path": str(input_path),
            "status": "pending",
            "run_dir": None,
            "moved_to": None,
            "error": None,
        }
        try:
            config = AgentConfig(
                input_path=input_path,
                out_dir=args.out_dir,
                backend=args.backend,
                macwhisper_bin=args.macwhisper_bin,
                macwhisper_model=args.macwhisper_model,
                polish=args.polish,
                openai_model=args.openai_model,
                glossary_path=args.glossary,
                input_is_transcript=False,
                auto_name=not args.no_auto_name,
                term_profile=args.term_profile,
            )
            run_dir = run(config)
            item["status"] = "done"
            item["run_dir"] = str(run_dir)

            if args.move_done:
                args.move_done.mkdir(parents=True, exist_ok=True)
                destination = unique_path(args.move_done / input_path.name)
                shutil.move(str(input_path), str(destination))
                item["moved_to"] = str(destination)
        except Exception as exc:
            item["status"] = "failed"
            item["error"] = str(exc)
        results.append(item)

        batch_summary_path.write_text(
            json.dumps(
                {
                    "batch_dir": str(args.batch_dir),
                    "out_dir": str(args.out_dir),
                    "polish": args.polish,
                    "count": len(files),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if not files:
        batch_summary_path.write_text(
            json.dumps(
                {
                    "batch_dir": str(args.batch_dir),
                    "out_dir": str(args.out_dir),
                    "polish": args.polish,
                    "count": 0,
                    "results": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return batch_summary_path


def main() -> None:
    args = parse_args()
    if args.batch_dir:
        batch_summary_path = run_batch(args)
        print(f"Batch done: {batch_summary_path}")
        return

    if not args.input:
        raise SystemExit("input is required unless --batch-dir is used.")

    config = AgentConfig(
        input_path=args.input,
        out_dir=args.out_dir,
        backend=args.backend,
        macwhisper_bin=args.macwhisper_bin,
        macwhisper_model=args.macwhisper_model,
        polish=args.polish,
        openai_model=args.openai_model,
        glossary_path=args.glossary,
        input_is_transcript=args.input_is_transcript,
        auto_name=not args.no_auto_name,
        term_profile=args.term_profile,
    )
    run_dir = run(config)
    print(f"Done: {run_dir}")


if __name__ == "__main__":
    main()
