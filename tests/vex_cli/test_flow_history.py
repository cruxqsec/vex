import asyncio

from vex_cli.models.pydantic import CaptureErrorEvent


def test_broadcast_reaches_every_subscriber(flow_history, request_summary):
    q1, q2 = flow_history.subscribe(), flow_history.subscribe()
    summary = request_summary()

    flow_history.broadcast(summary)

    assert q1.get_nowait() == summary
    assert q2.get_nowait() == summary


def test_broadcast_without_subscribers_does_not_raise(flow_history, request_summary):
    flow_history.broadcast(request_summary())


def test_broadcast_accepts_all_event_types_in_order(
    flow_history, request_summary, response_summary
):
    queue = flow_history.subscribe()
    events = [request_summary(), response_summary(), CaptureErrorEvent(message="boom")]

    for event in events:
        flow_history.broadcast(event)

    assert [queue.get_nowait() for _ in events] == events


def test_unsubscribed_queue_stops_receiving(flow_history, request_summary):
    staying, leaving = flow_history.subscribe(), flow_history.subscribe()
    flow_history.unsubscribe(leaving)

    flow_history.broadcast(request_summary())

    assert staying.qsize() == 1
    assert leaving.empty()


def test_unsubscribe_unknown_queue_does_not_raise(flow_history):
    flow_history.unsubscribe(asyncio.Queue())


def test_full_queue_drops_oldest_and_keeps_subscriber(flow_history, request_summary):
    queue = flow_history.subscribe()
    old = [request_summary() for _ in range(queue.maxsize)]
    for event in old:
        queue.put_nowait(event)
    newest = request_summary()

    flow_history.broadcast(newest)

    drained = [queue.get_nowait() for _ in range(queue.maxsize)]
    assert drained == old[1:] + [newest]


def test_full_queue_does_not_affect_other_subscribers(flow_history, request_summary):
    full, healthy = flow_history.subscribe(), flow_history.subscribe()
    for _ in range(full.maxsize):
        full.put_nowait(request_summary())
    event = request_summary()

    flow_history.broadcast(event)

    assert healthy.get_nowait() == event
