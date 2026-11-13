from __future__ import annotations

import subprocess
from pathlib import Path


class TranscriptionError(RuntimeError):
    pass


def transcribe_with_macwhisper(
    input_path: Path,
    *,
    macwhisper_bin: str = "mw",
    model: str | None = None,
) -> str:
    command = [macwhisper_bin, "transcribe", str(input_path)]
    if model:
        command.extend(["--model", model])

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "MacWhisper failed."
        raise TranscriptionError(message)
    return result.stdout.strip()

