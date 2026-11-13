from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .env import load_env_file


class PolishError(RuntimeError):
    pass


def complete_with_openai(prompt: str, *, model: str, temperature: float = 0.1) -> str:
    load_env_file()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise PolishError("OPENAI_API_KEY is not set. Put it in .env or export it in your shell.")

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "temperature": temperature,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise PolishError(f"OpenAI request failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise PolishError(f"OpenAI request failed: {exc}") from exc

    text = data.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
    if chunks:
        return "\n".join(chunks).strip()

    raise PolishError("OpenAI response did not contain output text.")


def polish_with_openai(prompt: str, *, model: str) -> str:
    return complete_with_openai(prompt, model=model, temperature=0.1)
