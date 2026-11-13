"""Evidence-backed terminology; ambiguous rules require an explicit course profile."""
from __future__ import annotations

import json
import re
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[2] / "resources" / "course_terms.json"


def correct_terms(text: str, profile: str = "shared") -> tuple[str, list[dict]]:
    if profile not in {"shared", "lesson5", "lesson6", "lesson7", "lesson8"}:
        raise ValueError(f"Unknown term profile: {profile}")
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = {r["wrong"]: r for r in data["rules"] if r["scope"] in {"shared", profile}}
    # A corrected English name may contain the original spelling as a prefix
    # (Richard -> Richards); match complete Latin words on repeated runs.
    pattern = re.compile("|".join(
        (r"(?<![A-Za-z])" if k[0].isascii() and k[0].isalpha() else "")
        + re.escape(k)
        + (r"(?![A-Za-z])" if k[-1].isascii() and k[-1].isalpha() else "")
        for k in sorted(rules, key=len, reverse=True)
    ))
    changes = []
    result = []
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        def replace(match: re.Match) -> str:
            rule = rules[match.group()]
            changes.append({"line": number, "before_line": line.rstrip(), **rule})
            return rule["correct"]
        result.append(pattern.sub(replace, line))
    return "".join(result), changes
