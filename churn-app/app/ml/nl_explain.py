"""Natural-language churn explanation via LLM (optional) with template fallback."""

from __future__ import annotations

import os
from functools import lru_cache

from app.config import OPENAI_API_KEY

AI_LABEL = "AI-generated summary — describes model patterns, not guaranteed causation."


def _template_explanation(
    risk_level: str,
    probability: float,
    factors: list[dict],
    attributes: dict | None = None,
) -> str:
    attrs = attributes or {}
    top = factors[:3] if factors else []
    parts = [f"Risk level: {risk_level} ({probability:.0f}% churn probability)."]
    if top:
        drivers = ", ".join(f["feature"] for f in top)
        parts.append(f"Primary drivers in the model: {drivers}.")
    tenure = attrs.get("tenure")
    contract = attrs.get("Contract") or attrs.get("contract")
    if tenure is not None and contract:
        parts.append(
            f"Customers with ~{tenure} months on a {contract} contract and similar billing "
            "patterns have historically churned more often in this dataset."
        )
    return " ".join(parts)


@lru_cache(maxsize=256)
def _cached_llm_key(payload_hash: str) -> str:
    return payload_hash


def generate_nl_explanation(
    risk_level: str,
    probability: float,
    factors: list[dict],
    attributes: dict | None = None,
) -> dict:
    """
    Returns {text, source: 'llm'|'template', ai_label}.
    Uses OpenAI when OPENAI_API_KEY is set; otherwise template fallback.
    """
    if not OPENAI_API_KEY:
        return {
            "text": _template_explanation(risk_level, probability, factors, attributes),
            "source": "template",
            "ai_label": AI_LABEL,
        }

    try:
        import httpx
        factor_lines = "\n".join(
            f"- {f.get('feature', '?')}: impact {f.get('impact', 0)}" for f in (factors or [])[:5]
        )
        prompt = (
            "Write 2-3 concise sentences explaining why this telecom customer has churn risk. "
            "Use plain English for a retention manager. Do not claim causation.\n\n"
            f"Risk: {risk_level}, probability: {probability}%\n"
            f"Top model factors:\n{factor_lines}\n"
            f"Attributes: {attributes or {}}\n"
        )
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You explain ML churn scores briefly and clearly."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 180,
                "temperature": 0.3,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return {"text": text, "source": "llm", "ai_label": AI_LABEL}
    except Exception:
        return {
            "text": _template_explanation(risk_level, probability, factors, attributes),
            "source": "template",
            "ai_label": AI_LABEL,
        }
