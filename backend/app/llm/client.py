"""Provider-agnostic LLM client with model fallback and SQLite caching.

The brief allows "any provider or open-source model" — this module makes that
literal. Three interchangeable backends behind one parse_structured() call:

- Groq   — open models on a free hosted tier (fast, daily token limits).
- Ollama — a local OpenAI-compatible server (gemma etc.): no token limits,
           fully offline. Slower and smaller, but always available.
- Anthropic — the premium option.

Resilience (Groq provider): each free Groq model has its own daily token
budget. When a call hits a 429 (or a model that can't emit clean JSON), the
client falls through to the next model in GROQ_FALLBACK_MODELS, and finally to
local Ollama if configured — so a run completes as long as ANY backend works.
Results cache under the intended model name, so a successful pass reproduces
instantly and for free on later runs.

Structured output: every backend uses JSON mode + the schema in the system
prompt, validated client-side with pydantic (one repair retry). Anthropic uses
its native structured-output parser.
"""
import hashlib
import json
import os

from pydantic import BaseModel, ValidationError

from ..config import (
    ANTHROPIC_MODEL,
    GROQ_API_KEY,
    GROQ_FALLBACK_MODELS,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    USE_OLLAMA_FALLBACK,
)
from ..db import get_conn

_groq = None
_ollama = None
_anthropic = None


class LLMNotConfigured(RuntimeError):
    """No API key / backend configured."""


class LLMQuotaExhausted(RuntimeError):
    """Every model in the fallback chain is rate-limited."""


# --- clients ----------------------------------------------------------------

def _groq_client():
    global _groq
    if _groq is None:
        if not GROQ_API_KEY:
            raise LLMNotConfigured("GROQ_API_KEY is not set — add it to backend/.env")
        from groq import Groq
        # max_retries=0: a daily-quota 429 won't clear by retrying (and the
        # retry-after can be minutes) — fail fast and switch models instead.
        _groq = Groq(api_key=GROQ_API_KEY, max_retries=0)
    return _groq


def _ollama_client():
    global _ollama
    if _ollama is None:
        from openai import OpenAI  # Ollama exposes an OpenAI-compatible API
        _ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", max_retries=0)
    return _ollama


def _anthropic_client():
    global _anthropic
    if _anthropic is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMNotConfigured("ANTHROPIC_API_KEY is not set — add it to backend/.env")
        import anthropic
        _anthropic = anthropic.Anthropic()
    return _anthropic


# --- helpers ----------------------------------------------------------------

def _cache_key(model: str, system: str, prompt: str, schema_name: str) -> str:
    payload = json.dumps(
        {"model": model, "system": system, "prompt": prompt, "schema": schema_name},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__
    return "RateLimit" in name or "429" in str(exc) or "rate_limit" in str(exc).lower()


def _is_recoverable(exc: Exception) -> bool:
    """A failure meaning *this model* can't do the job — fall through to the
    next. Covers rate-limits and JSON/schema failures."""
    s = str(exc).lower()
    return (
        _is_rate_limit(exc)
        or "json_validate_failed" in s
        or "failed to validate json" in s
        or "failed schema validation" in s
        or "json_object" in s
    )


def _chat_json(client, model: str, system: str, prompt: str,
               output_model: type[BaseModel], max_tokens: int) -> BaseModel:
    """One OpenAI-compatible JSON-mode call (Groq or Ollama) with a single
    pydantic-validation repair retry."""
    schema = json.dumps(output_model.model_json_schema(), indent=2)
    system_full = (
        f"{system}\n\n"
        f"Respond ONLY with a single JSON object that validates against this JSON schema "
        f"(no prose, no markdown fences):\n{schema}"
    )
    messages = [
        {"role": "system", "content": system_full},
        {"role": "user", "content": prompt},
    ]
    last_error: Exception | None = None
    for _ in range(2):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=min(max_tokens, 32768),
            temperature=0,
        )
        raw = response.choices[0].message.content or ""
        try:
            return output_model.model_validate_json(raw)
        except ValidationError as exc:
            last_error = exc
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content":
                    f"That JSON did not validate against the schema: {exc}. "
                    f"Return a corrected JSON object only."},
            ]
    raise RuntimeError(f"Response failed schema validation twice: {last_error}")


def _model_chain(primary: str) -> list[str]:
    return [primary] + [m for m in GROQ_FALLBACK_MODELS if m != primary]


def _call_groq(system, prompt, output_model, max_tokens, primary_model) -> BaseModel:
    """Try the Groq model chain, falling through whenever a model can't do the
    job (out of quota, or won't produce valid JSON)."""
    client = _groq_client()
    last_exc: Exception | None = None
    only_rate_limits = True
    for model in _model_chain(primary_model):
        try:
            result = _chat_json(client, model, system, prompt, output_model, max_tokens)
            print(f"[llm] groq:{model} ✓", flush=True)
            return result
        except Exception as exc:  # noqa: BLE001
            if _is_recoverable(exc):
                reason = "rate-limited" if _is_rate_limit(exc) else "bad JSON"
                print(f"[llm] groq:{model} {reason} → next", flush=True)
                last_exc = exc
                if not _is_rate_limit(exc):
                    only_rate_limits = False
                continue
            raise
    if only_rate_limits:
        raise LLMQuotaExhausted(
            "All free models have reached their daily limit. Please try again later "
            "(the Groq free-tier budget refills on a rolling 24h window)."
        ) from last_exc
    raise RuntimeError(f"No free Groq model could complete this step. Last error: {last_exc}") from last_exc


def _call_ollama(system, prompt, output_model, max_tokens) -> BaseModel:
    return _chat_json(_ollama_client(), OLLAMA_MODEL, system, prompt, output_model, max_tokens)


def _call_anthropic(system, prompt, output_model, max_tokens) -> BaseModel:
    response = _anthropic_client().messages.parse(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=output_model,
    )
    return response.parsed_output


# --- public -----------------------------------------------------------------

def parse_structured(system: str, prompt: str, output_model: type[BaseModel],
                     max_tokens: int = 16000, model: str | None = None,
                     allow_local_fallback: bool = True) -> BaseModel:
    """Structured-output call with caching and cross-backend fallback. Returns
    a validated pydantic object. `model` sets the preferred Groq model for this
    call; it still falls through the chain (and to local Ollama) if needed.
    Set `allow_local_fallback=False` for tasks a small local model handles
    poorly (e.g. free-form chat) — they raise LLMQuotaExhausted instead of
    returning a low-quality local answer."""
    if LLM_PROVIDER == "ollama":
        effective_model = OLLAMA_MODEL
    elif LLM_PROVIDER == "groq":
        effective_model = model or GROQ_MODEL
    else:
        effective_model = ANTHROPIC_MODEL

    key = _cache_key(effective_model, system, prompt, output_model.__name__)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT response FROM llm_cache WHERE cache_key = ?", (key,)
        ).fetchone()
    if row:
        return output_model.model_validate_json(row["response"])

    if LLM_PROVIDER == "ollama":
        result = _call_ollama(system, prompt, output_model, max_tokens)
    elif LLM_PROVIDER == "groq":
        try:
            result = _call_groq(system, prompt, output_model, max_tokens, effective_model)
        except (LLMQuotaExhausted, RuntimeError) as exc:
            # Last resort: local, unlimited Ollama. If it isn't running, surface
            # the original Groq exhaustion rather than a connection error.
            if USE_OLLAMA_FALLBACK and allow_local_fallback:
                try:
                    result = _call_ollama(system, prompt, output_model, max_tokens)
                except Exception:
                    raise exc
            else:
                raise
    else:
        result = _call_anthropic(system, prompt, output_model, max_tokens)

    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, response) VALUES (?, ?)",
            (key, result.model_dump_json()),
        )
    return result
