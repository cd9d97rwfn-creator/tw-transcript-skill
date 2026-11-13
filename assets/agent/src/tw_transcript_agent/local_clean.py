from __future__ import annotations

import re


CHAR_MAP = str.maketrans(
    {
        "简": "簡",
        "体": "體",
        "语": "語",
        "说": "說",
        "听": "聽",
        "写": "寫",
        "这": "這",
        "那": "那",
        "们": "們",
        "会": "會",
        "对": "對",
        "为": "為",
        "与": "與",
        "后": "後",
        "发": "發",
        "现": "現",
        "台": "臺",
        "里": "裡",
        "个": "個",
        "别": "別",
        "过": "過",
        "还": "還",
        "么": "麼",
        "样": "樣",
        "问": "問",
        "题": "題",
        "点": "點",
        "号": "號",
        "声": "聲",
        "频": "頻",
        "视": "視",
        "觉": "覺",
        "种": "種",
        "应": "應",
        "当": "當",
        "开": "開",
        "关": "關",
    }
)

PHRASE_MAP = {
    "台湾": "台灣",
    "繁体中文": "正體中文",
    "人工智能": "人工智慧",
    "视频": "影片",
    "音频": "音訊",
    "质量": "品質",
    "软件": "軟體",
    "数据": "資料",
    "网络": "網路",
}


def normalize_traditional(text: str) -> str:
    normalized = text.translate(CHAR_MAP)
    for source, target in PHRASE_MAP.items():
        normalized = normalized.replace(source, target)
    return normalized


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def add_light_punctuation(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if line[-1] not in "。！？；：,.!?":
            line += "。"
        lines.append(line)
    return "\n".join(lines)


def local_clean(text: str) -> str:
    text = normalize_whitespace(text)
    text = normalize_traditional(text)
    text = add_light_punctuation(text)
    return normalize_whitespace(text)

