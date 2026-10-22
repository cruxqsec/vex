import asyncio
import json
import logging
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from vex_cli.models.pydantic import FlowSummary, RequestSummary, ResponseSummary, VexServerInfo
from vex_client.api.client import ApiClient
from vex_client.history.manager import HistoryManager


def server(port=8000):
    return VexServerInfo(server_address="127.0.0.1", proxy_port=8080, api_port=port)


def request(flow_id=None, id=1):
    return RequestSummary(
        id=id, flow_id=flow_id or uuid4(), host="example.com", method="GET",
        path="/", request_size=10, is_tls=True, query=None,
        file_extension=None, timestamp=1.0,
    )


def response(flow_id):
    return ResponseSummary(
        flow_id=flow_id, status_code=200, response_size=20, mime="text/plain",
        http_title=None, cookie="", duration_ms=10, timestamp=2.0,
    )


def manager_with_callbacks():
    received = []
    loading = []
    manager = HistoryManager(
        lambda summary: received.append((summary, manager.summaries[summary.flow_id].status_code)),
        lambda state: loading.append((state, manager.is_loading)),
    )
    return manager, received, loading


def test_messages_update_cache_before_callback():
    manager, received, _ = manager_with_callbacks()
    req = request()
    res = response(req.flow_id)
    manager._handle_message(req.model_dump_json())
    manager._handle_message(res.model_dump_json())
    assert received == [(req, None), (res, 200)]
    assert manager.summaries[req.flow_id].response_size == 20
    manager.remove_summary(req.flow_id)
    assert not manager.summaries
    manager._handle_message(req.model_dump_json())
    manager.clear_summaries()
    assert not manager.summaries


async def test_receiver_collects_without_a_screen_and_cancellation_is_quiet(monkeypatch, caplog):
    manager, received, _ = manager_with_callbacks()
    info = server()
    manager.start_project()
    req = request()
    delivered = asyncio.Event()

    class WebSocket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not delivered.is_set():
                delivered.set()
                return req.model_dump_json()
            await asyncio.Event().wait()

    monkeypatch.setattr("vex_client.history.manager.websockets.connect", lambda uri: WebSocket())
    with caplog.at_level(logging.ERROR):
        task = asyncio.create_task(manager.receive_summaries(info))
        await delivered.wait()
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert req.flow_id in manager.summaries
    assert received[0][0] == req
    assert not caplog.text


def test_capture_error_is_logged_not_published(caplog):
    manager, received, _ = manager_with_callbacks()
    with caplog.at_level(logging.ERROR):
        manager._handle_message(json.dumps({"type": "capture_error", "message": "failed"}))
    assert not received
    assert "failed" in caplog.text


async def test_paginated_load_reports_loading_in_order():
    manager, _, loading = manager_with_callbacks()
    manager.start_project()
    items = [FlowSummary(**request(id=index).model_dump()) for index in range(51)]
    first_page_started = asyncio.Event()
    finish_first_page = asyncio.Event()

    async def fetch(skip, size):
        assert size == 50
        if skip == 0:
            first_page_started.set()
            await finish_first_page.wait()
            return items[:50]
        assert skip == 50
        return items[50:]

    api = SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=AsyncMock(side_effect=fetch)))
    task = asyncio.create_task(manager.load_summaries(cast(ApiClient, api)))
    await first_page_started.wait()
    assert manager.is_loading
    assert loading == [(True, True)]
    finish_first_page.set()
    await task
    assert len(manager.summaries) == 51
    assert loading == [(True, True), (False, False)]
    assert api.summaries.get_all_summaries.await_count == 2


@pytest.mark.parametrize("failure", [httpx.ConnectError("offline"), asyncio.CancelledError()])
async def test_failed_or_cancelled_load_clears_loading(failure, caplog):
    manager, _, loading = manager_with_callbacks()
    manager.start_project()
    api = SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=AsyncMock(side_effect=failure)))
    with caplog.at_level(logging.ERROR):
        if isinstance(failure, asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await manager.load_summaries(cast(ApiClient, api))
            assert "Could not load" not in caplog.text
        else:
            await manager.load_summaries(cast(ApiClient, api))
            assert "Could not load" in caplog.text
    assert not manager.is_loading
    assert loading == [(True, True), (False, False)]


@pytest.mark.parametrize("ignore_cancellation", [False, True])
async def test_stop_retains_data_and_obsolete_load_cannot_publish(ignore_cancellation):
    manager, _, loading = manager_with_callbacks()
    manager.start_project()
    retained = request()
    manager._handle_message(retained.model_dump_json())
    waiting = asyncio.Event()
    release = asyncio.Event()

    async def fetch(skip, size):
        waiting.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            if not ignore_cancellation:
                raise
        return [FlowSummary(**request().model_dump())]

    api = SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=fetch))
    task = asyncio.create_task(manager.load_summaries(cast(ApiClient, api)))
    await waiting.wait()
    manager.stop()
    assert retained.flow_id in manager.summaries
    assert not manager.is_loading
    manager.start_project()
    replacement = request()
    manager._handle_message(replacement.model_dump_json())
    release.set()
    if ignore_cancellation:
        await task
    else:
        with pytest.raises(asyncio.CancelledError):
            await task
    assert list(manager.summaries) == [replacement.flow_id]
    assert loading == [(True, True), (False, False)]


@pytest.mark.parametrize("transition", ["start_project", "clear_project"])
async def test_project_change_cancels_pending_load(transition):
    manager, _, _ = manager_with_callbacks()
    manager.start_project()
    started = asyncio.Event()

    async def fetch(skip, size):
        started.set()
        await asyncio.Event().wait()

    api = cast(ApiClient, SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=fetch)))
    task = asyncio.create_task(manager.load_summaries(api))
    await started.wait()
    getattr(manager, transition)()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not manager.is_loading
    assert not manager.summaries


async def test_cancelled_load_cleanup_does_not_clear_replacement_loading():
    manager, _, loading = manager_with_callbacks()
    manager.start_project()
    old_started = asyncio.Event()
    old_cleaning_up = asyncio.Event()
    finish_cleanup = asyncio.Event()
    new_started = asyncio.Event()
    finish_new_load = asyncio.Event()
    incoming = FlowSummary(**request().model_dump())

    async def old_fetch(skip, size):
        old_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            old_cleaning_up.set()
            await finish_cleanup.wait()
            raise

    async def new_fetch(skip, size):
        new_started.set()
        await finish_new_load.wait()
        return [incoming]

    old_api = cast(ApiClient, SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=old_fetch)))
    new_api = cast(ApiClient, SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=new_fetch)))
    old_task = asyncio.create_task(manager.load_summaries(old_api))
    new_task = None
    try:
        await old_started.wait()
        manager.start_project()
        await old_cleaning_up.wait()
        new_task = asyncio.create_task(manager.load_summaries(new_api))
        await new_started.wait()
        finish_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await old_task
        assert manager.is_loading
        assert loading == [(True, True), (False, False), (True, True)]

        finish_new_load.set()
        await new_task
        assert not manager.is_loading
        assert list(manager.summaries) == [incoming.flow_id]
    finally:
        old_task.cancel()
        if new_task is not None:
            new_task.cancel()
        await asyncio.gather(
            old_task, *([new_task] if new_task is not None else []), return_exceptions=True
        )


def test_each_project_start_discards_previous_summaries():
    manager, _, _ = manager_with_callbacks()
    manager.start_project()
    req = request()
    manager._handle_message(req.model_dump_json())
    manager.stop()
    assert req.flow_id in manager.summaries
    manager.start_project()
    assert not manager.summaries

