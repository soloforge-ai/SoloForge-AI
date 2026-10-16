"""Integration regressions for optional CI counter and durable Telegram delivery."""
import pytest

from backend import ops_telegram
from backend.ops_events import OpsEvent


def event(passed=True):
    return OpsEvent(
        event_key="test:ci", category="CI",
        event_type="ci.passed" if passed else "ci.failed",
        severity="info" if passed else "error", source="github",
        subject="Backend Test", status="SUCCESS" if passed else "FAILURE",
        commit_sha="abc123456789", details={"job_name": "backend-test", "job_id": 3, "run_id": 9},
    )


@pytest.mark.parametrize("mode", ["fail", "timeout", "unexpected", "verified"])
def test_delivery_isolation(monkeypatch, mode):
    calls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "dummy")
    monkeypatch.setattr(ops_telegram, "_claim", lambda _: {"id": 21})
    monkeypatch.setattr(ops_telegram, "_mark_sent", lambda _: calls.append("sent"))
    monkeypatch.setattr(ops_telegram, "_mark_failed", lambda *_: calls.append("failed"))
    monkeypatch.setattr(ops_telegram, "_send_telegram", lambda _t, _c, msg: calls.append(msg))

    def progress(_event):
        calls.append("lookup")
        if mode == "timeout":
            raise TimeoutError("API timed out")
        if mode == "unexpected":
            raise AssertionError("unexpected response shape")
        return (2, 3)

    monkeypatch.setattr(ops_telegram, "confirmed_progress", progress)
    assert ops_telegram.deliver_notification(event(passed=mode != "fail"), 21) is True
    assert calls[-1] == "sent"
    assert "failed" not in calls
    messages = [x for x in calls if isinstance(x, str) and "Commit:" in x]
    assert len(messages) == 1
    assert "abc12345" in messages[0]
    if mode == "fail":
        assert "lookup" not in calls
        assert "FAILURE" in messages[0]
    elif mode == "verified":
        assert "Progress: 2/3" in messages[0]
    else:
        assert "lookup" in calls
        assert "Progress:" not in messages[0]


def test_telegram_failure_keeps_outbox_failure_handling(monkeypatch):
    calls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "dummy")
    monkeypatch.setattr(ops_telegram, "_claim", lambda _: {"id": 22})
    monkeypatch.setattr(ops_telegram, "confirmed_progress", lambda _: (_ for _ in ()).throw(TimeoutError()))
    monkeypatch.setattr(ops_telegram, "_send_telegram", lambda *_: (_ for _ in ()).throw(RuntimeError("telegram down")))
    monkeypatch.setattr(ops_telegram, "_mark_failed", lambda i, e: calls.append((i, str(e))))
    monkeypatch.setattr(ops_telegram, "_mark_sent", lambda _: calls.append("sent"))
    with pytest.raises(RuntimeError, match="telegram down"):
        ops_telegram.deliver_notification(event(), 22)
    assert calls == [(22, "telegram down")]


def test_unclaimed_delivery_skips_counter_and_send(monkeypatch):
    monkeypatch.setattr(ops_telegram, "_claim", lambda _: None)
    monkeypatch.setattr(ops_telegram, "confirmed_progress", lambda _: pytest.fail("unexpected counter"))
    monkeypatch.setattr(ops_telegram, "_send_telegram", lambda *_: pytest.fail("unexpected send"))
    assert ops_telegram.deliver_notification(event(), 23) is False
