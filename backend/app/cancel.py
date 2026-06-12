"""Cooperative cancellation for the review pipeline.

The digest runs synchronously in a worker thread, so it can't be interrupted
from outside. Instead it checks this shared flag at safe points (before each
LLM call and during the rate-limit waits) and raises ReviewCancelled, which
unwinds the whole run. The cancel endpoint sets the flag from another thread.

Single global flag is enough here: only one review runs at a time.
"""
import threading

_event = threading.Event()


class ReviewCancelled(Exception):
    """Raised inside a running review when the user presses Stop."""


def request_cancel() -> None:
    _event.set()


def clear() -> None:
    _event.clear()


def is_cancelled() -> bool:
    return _event.is_set()


def raise_if_cancelled() -> None:
    if _event.is_set():
        raise ReviewCancelled()


def sleep(seconds: float) -> None:
    """Sleep, but wake and raise immediately if cancellation is requested."""
    if _event.wait(timeout=seconds):
        raise ReviewCancelled()
