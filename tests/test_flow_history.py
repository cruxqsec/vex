import pytest
import asyncio
from unittest.mock import MagicMock

from vex_cli.flow_history import FlowHistory
from vex_cli.models.pydantic import RequestSummary, ResponseSummary


@pytest.fixture
def flow_history():
    return FlowHistory()

@pytest.fixture
def mock_request_summary():
    return MagicMock(spec=RequestSummary)

@pytest.fixture
def mock_response_summary():
    return MagicMock(spec=ResponseSummary)


@pytest.mark.asyncio
async def test_subscribe_returns_queue(flow_history):
    queue = await flow_history.subscribe()

    assert isinstance(queue, asyncio.Queue)

@pytest.mark.asyncio
async def test_subscribe_adds_to_subscribers(flow_history):
    queue = await flow_history.subscribe()

    assert queue in flow_history._subscribers

@pytest.mark.asyncio
async def test_subscribe_multiple_returns_distinct_queues(flow_history):
    queue1 = await flow_history.subscribe()
    queue2 = await flow_history.subscribe()

    assert queue1 is not queue2
    assert len(flow_history._subscribers) == 2

@pytest.mark.asyncio
async def test_subscribe_queue_has_correct_maxsize(flow_history):
    queue = await flow_history.subscribe()

    assert queue.maxsize == 100


@pytest.mark.asyncio
async def test_unsubscribe_removes_queue(flow_history):
    queue = await flow_history.subscribe()

    await flow_history.unsubscribe(queue)

    assert queue not in flow_history._subscribers

@pytest.mark.asyncio
async def test_unsubscribe_nonexistent_queue_does_not_raise(flow_history):
    ghost_queue = asyncio.Queue()

    await flow_history.unsubscribe(ghost_queue)  # should not raise

@pytest.mark.asyncio
async def test_unsubscribe_only_removes_target_queue(flow_history):
    queue1 = await flow_history.subscribe()
    queue2 = await flow_history.subscribe()

    await flow_history.unsubscribe(queue1)

    assert queue1 not in flow_history._subscribers
    assert queue2 in flow_history._subscribers


@pytest.mark.asyncio
async def test_broadcast_delivers_to_subscriber(flow_history, mock_request_summary):
    queue = await flow_history.subscribe()

    await flow_history.broadcast_summary(mock_request_summary)

    assert queue.get_nowait() is mock_request_summary

@pytest.mark.asyncio
async def test_broadcast_delivers_to_all_subscribers(flow_history, mock_request_summary):
    queue1 = await flow_history.subscribe()
    queue2 = await flow_history.subscribe()

    await flow_history.broadcast_summary(mock_request_summary)

    assert queue1.get_nowait() is mock_request_summary
    assert queue2.get_nowait() is mock_request_summary

@pytest.mark.asyncio
async def test_broadcast_with_no_subscribers_does_not_raise(flow_history, mock_request_summary):
    await flow_history.broadcast_summary(mock_request_summary)  # should not raise

@pytest.mark.asyncio
async def test_broadcast_works_with_response_summary(flow_history, mock_response_summary):
    queue = await flow_history.subscribe()

    await flow_history.broadcast_summary(mock_response_summary)

    assert queue.get_nowait() is mock_response_summary

@pytest.mark.asyncio
async def test_broadcast_removes_full_queue(flow_history, mock_request_summary):
    queue = await flow_history.subscribe()

    # fill the queue to maxsize
    for _ in range(100):
        await queue.put(MagicMock())

    await flow_history.broadcast_summary(mock_request_summary)

    assert queue not in flow_history._subscribers

@pytest.mark.asyncio
async def test_broadcast_removes_only_full_queues(flow_history, mock_request_summary):
    full_queue = await flow_history.subscribe()
    healthy_queue = await flow_history.subscribe()

    for _ in range(100):
        await full_queue.put(MagicMock())

    await flow_history.broadcast_summary(mock_request_summary)

    assert full_queue not in flow_history._subscribers
    assert healthy_queue in flow_history._subscribers

@pytest.mark.asyncio
async def test_broadcast_multiple_messages_in_order(flow_history):
    queue = await flow_history.subscribe()
    summaries = [MagicMock(spec=RequestSummary) for _ in range(3)]

    for s in summaries:
        await flow_history.broadcast_summary(s)

    for s in summaries:
        assert queue.get_nowait() is s