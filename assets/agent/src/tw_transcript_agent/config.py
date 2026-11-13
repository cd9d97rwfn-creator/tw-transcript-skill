from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_MACWHISPER_BIN = Path("/Applications/MacWhisper.app/Contents/MacOS/mw")


def default_macwhisper_bin() -> str:
    if DEFAULT_MACWHISPER_BIN.exists():
        return str(DEFAULT_MACWHISPER_BIN)
    return "mw"


@dataclass(frozen=True)
class AgentConfig:
    input_path: Path
    out_dir: Path
    backend: str = "macwhisper"
    macwhisper_bin: str = default_macwhisper_bin()
    macwhisper_model: str | None = None
    polish: str = "local"
    openai_model: str = "gpt-4.1-mini"
    glossary_path: Path | None = None
    language_note: str = "台灣正體中文"
    input_is_transcript: bool = False
    auto_name: bool = True
    term_profile: str = "shared"
