from __future__ import annotations

from cricket_posts import ideogram


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_ideogram_retries_transient_failures(monkeypatch):
    responses = iter([FakeResponse(429), FakeResponse(503), FakeResponse(200)])
    calls: list[int] = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return next(responses)

    monkeypatch.setattr(ideogram.requests, "post", fake_post)
    monkeypatch.setattr(ideogram.time, "sleep", lambda _seconds: None)

    result = ideogram._request_with_retries(
        headers={"Api-Key": "test"},
        files={"text_prompt": (None, "text-free cricket art")},
    )

    assert result.status_code == 200
    assert len(calls) == 3


def test_ideogram_does_not_retry_validation_errors(monkeypatch):
    calls: list[int] = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(422)

    monkeypatch.setattr(ideogram.requests, "post", fake_post)
    result = ideogram._request_with_retries(
        headers={"Api-Key": "test"},
        files={"json_prompt": (None, "{}")},
    )

    assert result.status_code == 422
    assert len(calls) == 1
