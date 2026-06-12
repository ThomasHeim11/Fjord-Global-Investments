"""Cooperative cancellation of a running review."""
import time

import pytest

from app import cancel


def test_raise_if_cancelled():
    cancel.clear()
    cancel.raise_if_cancelled()  # no-op when not set
    cancel.request_cancel()
    with pytest.raises(cancel.ReviewCancelled):
        cancel.raise_if_cancelled()


def test_sleep_returns_normally_when_not_cancelled():
    cancel.clear()
    start = time.monotonic()
    cancel.sleep(0.05)
    assert time.monotonic() - start >= 0.04


def test_sleep_wakes_and_raises_when_cancelled():
    cancel.request_cancel()
    start = time.monotonic()
    with pytest.raises(cancel.ReviewCancelled):
        cancel.sleep(5)  # would block 5s, but cancel is already set
    assert time.monotonic() - start < 1  # returned ~immediately


def test_clear_resets_the_flag():
    cancel.request_cancel()
    assert cancel.is_cancelled()
    cancel.clear()
    assert not cancel.is_cancelled()


def test_throttle_raises_when_cancelled(monkeypatch):
    # the throttle runs before every Groq call, so it's where cancel bites
    from app.llm import client

    cancel.request_cancel()
    with pytest.raises(cancel.ReviewCancelled):
        client._throttle_groq()
