"""LLM client plumbing: cache key stability, rate-limit parsing, the model
fallback chain, and the cache read/write/bypass behaviour that the live-vs-
cached review depends on. No network is touched — the provider call is stubbed.
"""
from pydantic import BaseModel

from app.llm import client


def test_cache_key_is_deterministic_and_sensitive():
    a = client._cache_key("m", "sys", "prompt", "Schema")
    b = client._cache_key("m", "sys", "prompt", "Schema")
    assert a == b
    assert a != client._cache_key("m2", "sys", "prompt", "Schema")
    assert a != client._cache_key("m", "sys", "prompt2", "Schema")


def test_model_chain_puts_primary_first_without_duplicates():
    chain = client._model_chain("llama-3.1-8b-instant")
    assert chain[0] == "llama-3.1-8b-instant"
    assert chain.count("llama-3.1-8b-instant") == 1
    assert set(chain) >= set(client.GROQ_FALLBACK_MODELS)


def test_rate_limit_detection():
    assert client._is_rate_limit(Exception("Error code: 429 rate_limit_exceeded"))
    assert not client._is_rate_limit(Exception("some other error"))


def test_recoverable_covers_rate_limit_and_bad_json():
    assert client._is_recoverable(Exception("429 rate_limit"))
    assert client._is_recoverable(Exception("json_validate_failed"))
    assert not client._is_recoverable(Exception("connection refused"))


def test_retry_after_parsed_from_message():
    assert client._retry_after_seconds(Exception("Please try again in 6.5s.")) == 6.5
    assert client._retry_after_seconds(Exception("try again in 12s")) == 12.0


def test_retry_after_defaults_to_zero_when_absent():
    assert client._retry_after_seconds(Exception("nope")) == 0.0


def test_retry_after_reads_header():
    class Resp:
        headers = {"retry-after": "7"}

    exc = Exception("limited")
    exc.response = Resp()
    assert client._retry_after_seconds(exc) == 7.0


# --- caching / bypass -------------------------------------------------------

class _Out(BaseModel):
    value: str


def test_parse_structured_caches_then_replays(db, monkeypatch):
    monkeypatch.setattr(client, "LLM_PROVIDER", "groq")
    calls = {"n": 0}

    def fake_groq(system, prompt, output_model, max_tokens, primary_model):
        calls["n"] += 1
        return output_model(value=f"answer-{calls['n']}")

    monkeypatch.setattr(client, "_call_groq", fake_groq)
    client.set_bypass_cache(False)

    first = client.parse_structured("sys", "prompt", _Out)
    assert first.value == "answer-1"
    assert calls["n"] == 1

    # identical call is served from cache: provider not hit again
    second = client.parse_structured("sys", "prompt", _Out)
    assert second.value == "answer-1"
    assert calls["n"] == 1


def test_bypass_forces_live_call_but_still_writes_cache(db, monkeypatch):
    monkeypatch.setattr(client, "LLM_PROVIDER", "groq")
    calls = {"n": 0}

    def fake_groq(system, prompt, output_model, max_tokens, primary_model):
        calls["n"] += 1
        return output_model(value=f"answer-{calls['n']}")

    monkeypatch.setattr(client, "_call_groq", fake_groq)

    client.set_bypass_cache(False)
    client.parse_structured("sys", "prompt", _Out)        # caches answer-1
    assert calls["n"] == 1

    client.set_bypass_cache(True)
    live = client.parse_structured("sys", "prompt", _Out)  # ignores cache on read
    assert live.value == "answer-2"
    assert calls["n"] == 2

    # bypass still wrote, so a later normal call replays the fresh answer
    client.set_bypass_cache(False)
    replay = client.parse_structured("sys", "prompt", _Out)
    assert replay.value == "answer-2"
    assert calls["n"] == 2
