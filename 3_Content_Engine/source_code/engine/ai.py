"""Optional OpenAI-compatible hook transformation with strict offline fallback.

No provider is contacted unless ``--ai`` is passed. Credentials and endpoint are
read only from environment variables; the deterministic engine remains the default.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request

log = logging.getLogger("engine")


class AIUnavailable(RuntimeError):
    """Raised when optional AI is misconfigured, unavailable, or unsafe."""


def _source_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _safe_rewrite(original, proposed, source_sentence, source_text, max_words):
    if not isinstance(proposed, str) or not 4 <= len(proposed.split()) <= max_words:
        return False
    if source_sentence not in source_text:
        return False
    original_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", source_text))
    if set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", proposed)) - original_numbers:
        return False
    # A rewrite must retain enough source vocabulary to remain traceable.
    a = set(re.findall(r"[a-z]{3,}", proposed.lower()))
    b = set(re.findall(r"[a-z]{3,}", source_sentence.lower()))
    return bool(a) and len(a & b) / len(a) >= 0.45


def transform_hooks(specs, source_text, max_words, timeout=20):
    """Return transformed specs and metadata, or raise ``AIUnavailable``.

    The provider may rewrite hooks only. Source points, claims, URLs, and IDs are
    immutable. Every accepted rewrite must cite a verbatim source sentence.
    """
    key = os.getenv("INCUBRIX_AI_API_KEY", "").strip()
    base = os.getenv("INCUBRIX_AI_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("INCUBRIX_AI_MODEL", "").strip()
    if not key or not base or not model:
        raise AIUnavailable(
            "set INCUBRIX_AI_API_KEY, INCUBRIX_AI_BASE_URL, and INCUBRIX_AI_MODEL"
        )
    compact = [
        {"asset_id": s["asset_id"], "platform": s["platform"], "format": s["format"], "hook": s["hook"]}
        for s in specs
    ]
    prompt = {
        "task": "Rewrite each hook for its platform without adding facts, features, statistics, or testimonials.",
        "rules": [
            f"4-{max_words} words",
            "sentence case",
            "cite one verbatim source_sentence for every hook",
            "return JSON only: {items:[{asset_id,hook,source_sentence}]}",
        ],
        "source_sentences": _source_sentences(source_text),
        "assets": compact,
    }
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You edit social hooks. Never invent or infer facts."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.load(response)
        content = payload["choices"][0]["message"]["content"]
        items = json.loads(content)["items"]
    except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AIUnavailable(f"provider response unavailable or invalid: {exc}") from exc
    proposed = {item.get("asset_id"): item for item in items if isinstance(item, dict)}
    accepted = 0
    result = []
    for spec in specs:
        copy = dict(spec)
        item = proposed.get(spec["asset_id"], {})
        hook = item.get("hook")
        source = item.get("source_sentence")
        if _safe_rewrite(spec["hook"], hook, source, source_text, max_words):
            copy["hook"] = hook.strip()
            copy["ai_trace"] = {"source_sentence": source, "original_hook": spec["hook"]}
            accepted += 1
        result.append(copy)
    if not accepted:
        raise AIUnavailable("no provider rewrites passed source-traceability validation")
    return result, {"mode": "ai", "model": model, "accepted_rewrites": accepted}
