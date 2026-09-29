"""LLM access behind one interface — vendor-independent per spec (Principle 6)."""
import os
from typing import Any


def complete(prompt: str, system: str = "") -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return _openai(prompt, system)
    if provider == "anthropic":
        return _anthropic(prompt, system)
    raise RuntimeError(f"unsupported LLM_PROVIDER={provider}")


def _openai(prompt: str, system: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=messages,  # type: ignore[arg-type]
    )
    return resp.choices[0].message.content or ""


def _anthropic(prompt: str, system: str) -> str:
    import anthropic  # type: ignore
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs: dict[str, Any] = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)  # type: ignore[arg-type]
    parts = [getattr(b, "text", "") for b in resp.content]
    return "".join(p for p in parts if isinstance(p, str))
