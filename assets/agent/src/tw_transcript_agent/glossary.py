from __future__ import annotations

from pathlib import Path


def load_glossary(path: Path | None) -> list[tuple[str, str]]:
    if path is None or not path.exists():
        return []

    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in stripped:
            wrong, correct = stripped.split("\t", 1)
        elif "," in stripped:
            wrong, correct = stripped.split(",", 1)
        else:
            continue
        wrong = wrong.strip()
        correct = correct.strip()
        if wrong and correct:
            pairs.append((wrong, correct))
    return pairs


def apply_glossary(text: str, pairs: list[tuple[str, str]]) -> str:
    cleaned = text
    for wrong, correct in pairs:
        cleaned = cleaned.replace(wrong, correct)
    return cleaned


def glossary_for_prompt(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "（無）"
    return "\n".join(f"- {wrong} -> {correct}" for wrong, correct in pairs)

