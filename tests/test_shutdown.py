import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

import relay


@pytest.fixture
def fake_relay(monkeypatch):
    instance = Mock()
    instance._runner = object()
    instance.end_background = AsyncMock()
    monkeypatch.setattr(relay, 'get_backend', Mock())
    monkeypatch.setattr(relay, 'RelaySQLiteEventStore', Mock())
    monkeypatch.setattr(relay, 'PQRelay', Mock(return_value=instance))
    return instance


@pytest.mark.asyncio
async def test_cancellation_cleans_up_and_propagates(fake_relay):
    entered = asyncio.Event()

    async def start(**kwargs):
        entered.set()
        await asyncio.Event().wait()

    fake_relay.start = start
    task = asyncio.create_task(relay.run_relay())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    fake_relay.end_background.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('runner_created', [True, False])
async def test_startup_errors_are_not_swallowed(fake_relay, runner_created):
    fake_relay._runner = object() if runner_created else None
    fake_relay.start = AsyncMock(side_effect=OSError('port unavailable'))
    with pytest.raises(OSError, match='port unavailable'):
        await relay.run_relay()
    assert fake_relay.end_background.await_count == int(runner_created)


def test_ctrl_c_is_reported_without_traceback(monkeypatch, caplog):
    def interrupted(coroutine):
        coroutine.close()
        raise KeyboardInterrupt()

    monkeypatch.setattr(relay.asyncio, 'run', interrupted)
    relay.main()
    assert 'Relay stopped' in caplog.text


def test_entrypoint_preserves_real_errors(monkeypatch):
    def failed(coroutine):
        coroutine.close()
        raise RuntimeError('backend failure')

    monkeypatch.setattr(relay.asyncio, 'run', failed)
    with pytest.raises(RuntimeError, match='backend failure'):
        relay.main()
