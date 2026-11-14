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


def complete(system: str, user: str, max_tokens: int = 8000, temperature: float = 0.4) -> str:
    """One chat turn with retry. Thinking models sometimes burn the whole budget
    on reasoning and return no text; escalate once, then fail loudly."""
    budget = max_tokens
    for attempt in (1, 2):
        text = _complete_once(system, user, budget, temperature)
        if text.strip():
            return text
        budget = min(budget * 3, 32000)
    raise RuntimeError(
        f"Model returned no text after 2 attempts (thinking-only). Try ANTHROPIC_MODEL=abliterated-model-large-flash."
    )


def _complete_once(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """One chat turn, returns text. Handles model-name normalization for proxies."""
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    base = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    url = f"{base}/v1/messages"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
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
    return text


def complete_json(system: str, user: str, max_tokens: int = 6000) -> dict:
    """Ask for strict JSON, strip fences, parse."""
    text = complete(system + "\nRespond with valid JSON only, no fences.", user, max_tokens)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text.lstrip()
    return json.loads(text.strip())
