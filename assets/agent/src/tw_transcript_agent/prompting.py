from __future__ import annotations

from .glossary import glossary_for_prompt


def build_polish_prompt(
    transcript: str,
    glossary_pairs: list[tuple[str, str]],
    *,
    language_note: str = "台灣正體中文",
) -> str:
    glossary = glossary_for_prompt(glossary_pairs)
    return f"""你是一位專業逐字稿校對員，任務是把機器轉錄稿整理成忠實、自然、可讀的{language_note}逐字稿。

請嚴格遵守：
1. 不摘要、不擴寫、不加入原音訊沒有的內容。
2. 保留說話者原本的意思、語氣與順序。
3. 將簡體字轉為台灣常用正體中文。
4. 補上自然標點與段落，但不要過度文學化。
5. 修正明顯聽錯、同音錯字、專有名詞錯誤。學校、機構、人名、學派、理論、方法、書名與外文名稱須以提供的已核實詞彙及上下文為準，不可僅憑發音猜造；不可用一般正確知識改寫講者的原始主張。
6. 可以刪除或整理不影響語意的贅字、填充詞、卡頓與重複起頭，例如「呃」「嗯」「就是」「那個」「然後然後」，但不要刪除任何新的資訊、例子、轉折、情緒或語氣重點。
7. 若只有逐字稿而沒有回聽音訊，無法確認的詞保留原文並標記「[辨識待確認]」，不可聲稱「聽不清」或已回聽。保留既有時間戳記。
8. 輸出只需要校稿後逐字稿，不要解釋你的修改。

優先使用以下詞彙修正表：
{glossary}

原始逐字稿如下：
---
{transcript}
---"""
