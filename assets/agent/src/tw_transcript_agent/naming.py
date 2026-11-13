from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .polisher import complete_with_openai


GENERIC_WORDS = {
    "raw",
    "transcript",
    "逐字稿",
    "錄音",
    "音檔",
    "影片",
    "小卡",
}


def extract_date_from_text(text: str) -> str | None:
    compact = re.search(r"(20\d{2})([01]\d)([0-3]\d)", text)
    if compact:
        return f"{compact.group(1)}-{compact.group(2)}-{compact.group(3)}"

    dashed = re.search(r"(20\d{2})[-_/年.]([01]?\d)[-_/月.]([0-3]?\d)", text)
    if dashed:
        year, month, day = dashed.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    return None


def infer_date(input_path: Path) -> str:
    for candidate in [input_path.name, str(input_path)]:
        found = extract_date_from_text(candidate)
        if found:
            return found
    return datetime.now().strftime("%Y-%m-%d")


def sanitize_topic(topic: str) -> str:
    topic = topic.strip()
    topic = re.sub(r"[\\/:*?\"<>|#]+", "", topic)
    topic = re.sub(r"\s+", "-", topic)
    topic = re.sub(r"-{2,}", "-", topic)
    topic = topic.strip("-. ")
    return topic[:48] or "未命名逐字稿"


def infer_topic_from_path(input_path: Path) -> str:
    stem = input_path.stem
    stem = re.sub(r"20\d{6}", "", stem)
    stem = re.sub(r"20\d{2}[-_/年.]([01]?\d)[-_/月.]([0-3]?\d)", "", stem)
    parts = [part for part in re.split(r"[\s_-]+", stem) if part and part not in GENERIC_WORDS]
    return sanitize_topic(" ".join(parts) or input_path.stem)


def infer_topic_with_openai(text: str, *, model: str, fallback: str) -> str:
    sample = text[:6000]
    prompt = f"""請根據以下逐字稿，產生一個適合檔名使用的核心主題。

規則：
1. 使用台灣正體中文。
2. 8 到 24 個字。
3. 不要加日期。
4. 不要使用冒號、斜線、引號或檔名不安全符號。
5. 只輸出 JSON，格式為 {{"topic":"主題"}}。

逐字稿：
---
{sample}
---"""
    try:
        response = complete_with_openai(prompt, model=model)
        data = json.loads(response)
        topic = data.get("topic")
        if isinstance(topic, str) and topic.strip():
            return sanitize_topic(topic)
    except Exception:
        return fallback
    return fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(path)


def build_final_filename(date_text: str, topic: str) -> str:
    return f"{date_text}-{sanitize_topic(topic)}.md"

