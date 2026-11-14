"""Single LLM client that works with either Claude key or Abliterated proxy.

Config (via .env or environment):
  ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY  required unless --mock
  ANTHROPIC_BASE_URL   optional, e.g. Abliterated's Anthropic-compatible endpoint
  ANTHROPIC_MODEL      optional, default claude-sonnet-4-5-20250929 (proxy overrides allowed)

If the `anthropic` package is missing, falls back to raw HTTP against the
Messages API so the proxy case (base_url override) keeps working.
"""
import json
import os
import urllib.request

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def _auth():
    tok = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not tok:
        raise RuntimeError(
            "No key. Set ANTHROPIC_AUTH_TOKEN (proxy) or ANTHROPIC_API_KEY in the environment "
            "or 02_AUTOMATION/revanew_pipeline/.env"
        )
    return tok


def _complete_once(system, messages, max_tokens, temperature):
    """One API turn. Returns (text, stop_reason)."""
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    base = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    url = f"{base}/v1/messages"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages,
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": _auth(),
        "authorization": f"Bearer {_auth()}",
        "anthropic-version": "2023-06-01",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return text, data.get("stop_reason")


def complete(system: str, user: str, max_tokens: int = 12000, temperature: float = 0.4) -> str:
    """One chat turn, auto-continuing truncated output and retrying thinking-empty turns."""
    messages = [{"role": "user", "content": user}]
    budget = max_tokens
    out = ""
    empty_left = 2
    while True:
        text, stop = _complete_once(system, messages, budget, temperature)
        if not text.strip():
            empty_left -= 1
            if empty_left <= 0:
                raise RuntimeError("Model returned no text after retries (thinking-only).")
            budget = min(budget * 3, 32000)
            continue
        out += text
        messages.append({"role": "assistant", "content": text})
        if stop == "max_tokens" and len(out) < 120000:
            messages.append({"role": "user", "content": "Continue exactly where you stopped. No preamble, no repeat."})
            budget = min(max(budget, 16000), 32000)
            continue
        return out


def complete_json(system: str, user: str, max_tokens: int = 6000) -> dict:
    """Ask for strict JSON, strip fences, parse."""
    text = complete(system + "\nRespond with valid JSON only, no fences.", user, max_tokens)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text.lstrip()
    return json.loads(text.strip())
