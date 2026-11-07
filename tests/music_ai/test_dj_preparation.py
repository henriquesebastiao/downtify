from dataclasses import FrozenInstanceError
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from downtify.music_ai.dj_preparation import (
    PreparationResult,
    SinglePreparation,
)


def reap(preparation):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        result = preparation.poll()
        if result is not None:
            return result
        sleep(0.001)
    pytest.fail('Preparation did not finish')


def test_single_slot_and_poll_remain_nonblocking_until_reaped():
    preparation = SinglePreparation()
    started, release, polled = Event(), Event(), Event()
    observed = []

    def work(checkpoint):
        started.set()
        assert release.wait(3)
        checkpoint()
        return 'pcm'

    def poll():
        observed.append(preparation.poll())
        polled.set()

    try:
        assert preparation.poll() is None
        assert preparation.submit(('generation', 1), work)
        assert started.wait(3)
        assert preparation.busy
        assert not preparation.submit('second', lambda check: None)
        thread = Thread(target=poll)
        thread.start()
        try:
            assert polled.wait(1), 'poll blocked behind running work'
        finally:
            release.set()
            thread.join(3)
        assert observed == [None]
        # Completion itself must not free the single slot.
        preparation._future.result(timeout=3)
        assert preparation.busy
        assert not preparation.submit('second', lambda check: None)
        result = reap(preparation)
        assert result == PreparationResult(('generation', 1), 'pcm', None, False)
        assert not preparation.busy
        assert preparation.poll() is None
        assert preparation.submit('second', lambda check: 2)
        assert reap(preparation).value == 2
    finally:
        release.set()
        preparation.close()


def test_error_is_returned_with_key_and_result_is_immutable():
    preparation = SinglePreparation()
    failure = ValueError('failed preparation')

    def work(checkpoint):
        raise failure

    try:
        assert preparation.submit('source-version', work)
        result = reap(preparation)
        assert result.key == 'source-version'
        assert result.value is None
        assert result.error is failure
        assert not result.cancelled
        with pytest.raises(FrozenInstanceError):
            result.key = 'changed'
    finally:
        preparation.close()


def test_cancellation_is_cooperative_and_keeps_slot_until_reaped():
    preparation = SinglePreparation()
    started, release, cleaned = Event(), Event(), Event()

    def work(checkpoint):
        try:
            started.set()
            assert release.wait(3)
            checkpoint()
            pytest.fail('Cancelled work continued')
        finally:
            cleaned.set()

    try:
        assert preparation.submit('cancelled-key', work)
        assert started.wait(3)
        preparation.cancel()
        preparation.cancel()
        assert preparation.busy
        assert preparation.poll() is None
        assert not preparation.submit('second', lambda check: None)
        release.set()
        result = reap(preparation)
        assert cleaned.is_set()
        assert result.key == 'cancelled-key'
        assert result.cancelled
        assert isinstance(result.error, PermissionError)
        assert not preparation.busy
    finally:
        release.set()
        preparation.close()


def test_close_waits_for_cleanup_and_retains_late_value_for_disposal():
    preparation = SinglePreparation()
    started, cleanup_started, cleanup_release, closed = (
        Event(), Event(), Event(), Event()
    )

    def work(checkpoint):
        started.set()
        try:
            while True:
                checkpoint()
                sleep(0.001)
        except PermissionError:
            # Model a result produced just as cancellation takes effect.
            return 'late-private-file'
        finally:
            cleanup_started.set()
            assert cleanup_release.wait(3)

    def close():
        preparation.close()
        closed.set()

    closer = Thread(target=close)
    try:
        assert preparation.submit('old-generation', work)
        assert started.wait(3)
        closer.start()
        assert cleanup_started.wait(3)
        assert not closed.is_set()
        assert preparation.busy
        assert not preparation.submit('second', lambda check: None)
        cleanup_release.set()
        assert closed.wait(3)
        closer.join(3)
        preparation.close()
        result = preparation.poll()
        assert result == PreparationResult(
            'old-generation', 'late-private-file', None, True
        )
        assert not preparation.busy
        assert not preparation.submit('after-close', lambda check: None)
    finally:
        cleanup_release.set()
        if closer.ident is not None:
            closer.join(3)
        preparation.close()


def test_close_without_work_is_idempotent_and_rejects_submission():
    preparation = SinglePreparation()
    preparation.cancel()
    preparation.close()
    preparation.close()
    assert preparation.poll() is None
    assert not preparation.busy
    assert not preparation.submit('closed', lambda check: None)
