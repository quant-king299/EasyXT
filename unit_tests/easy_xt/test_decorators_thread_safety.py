import threading
import time

import pytest

from easy_xt.decorators import rate_limit


def test_rate_limit_rejects_non_positive_rates():
    with pytest.raises(ValueError, match='必须大于0'):
        rate_limit(0)

    with pytest.raises(ValueError, match='必须大于0'):
        rate_limit(-1)


def test_rate_limit_serializes_time_slots_across_threads():
    starts = []
    starts_lock = threading.Lock()
    ready = threading.Barrier(4)

    @rate_limit(calls_per_second=50)
    def record_start():
        with starts_lock:
            starts.append(time.monotonic())

    def worker():
        ready.wait()
        record_start()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert all(not thread.is_alive() for thread in threads)
    ordered = sorted(starts)
    assert len(ordered) == 4
    assert all(
        later - earlier >= 0.015
        for earlier, later in zip(ordered, ordered[1:])
    )
