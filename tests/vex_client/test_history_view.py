import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from vex_cli.models.pydantic import RequestSummary, ResponseSummary, Scope
from vex_client.api.client import ApiClient
from vex_client.history.query import parse_search_query
from vex_client.widgets.table import SortOrder

pytestmark = pytest.mark.asyncio


def request(number, host="example.test"):
    return RequestSummary(
        id=number, flow_id=uuid4(), host=host, method="GET", path="/",
        request_size=10, is_tls=True, query=None, file_extension=None,
        timestamp=float(number),
    )


def response(summary, status=200, size=0):
    return ResponseSummary(
        flow_id=summary.flow_id, status_code=status, response_size=size,
        mime="text/plain", http_title=None, cookie="", duration_ms=0,
        timestamp=float(summary.id),
    )



def deliver(app, *summaries):
    for summary in summaries:
        app.history_manager._handle_message(summary.model_dump_json())


def row_ids(screen):
    return [row.key.value for row in screen.http_table.ordered_rows]


def ids(*summaries):
    return [str(summary.flow_id) for summary in summaries]


async def submit(pilot, screen, text):
    screen.search_bar.focus()
    screen.search_bar.value = text
    screen.search_bar.cursor_position = len(text)
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


async def select(pilot, screen, summary):
    screen.http_table.focus()
    screen.http_table.move_cursor(
        row=screen.http_table.get_row_index(str(summary.flow_id)), animate=False
    )
    await pilot.press("enter")
    await pilot.pause()


def assert_no_raw_fetch(api):
    api.raw.get_raw_request.assert_not_awaited()
    api.raw.get_raw_response.assert_not_awaited()


@pytest.mark.parametrize("invalid", ["unknown:value", "status:"])
async def test_search_enter_applies_but_drafts_and_invalid_submission_do_not(
    history_app, opened_history, monkeypatch, invalid
):
    async with opened_history(history_app) as (pilot, screen, api):
        first = request(1, "alpha.test")
        second = request(2, "beta.test")
        deliver(history_app, first, second)
        await pilot.pause()
        screen.search_bar.focus()
        screen.search_bar.value = "host:alpha.test"
        await pilot.pause()
        assert row_ids(screen) == ids(first, second)
        assert screen.applied_search == ()

        await submit(pilot, screen, "host:alpha.test")
        applied = parse_search_query("host:alpha.test")
        assert screen.applied_search == applied
        assert row_ids(screen) == ids(first)

        screen.search_bar.value = "host:beta.test"
        third = request(3, "alpha.test")
        deliver(history_app, third)
        await pilot.pause()
        assert screen.applied_search == applied
        assert row_ids(screen) == ids(first, third)

        notify = Mock()
        monkeypatch.setattr(screen, "notify", notify)
        await submit(pilot, screen, invalid)
        assert screen.search_bar.value == invalid
        assert screen.applied_search == applied
        assert row_ids(screen) == ids(first, third)
        notify.assert_called_once()
        assert notify.call_args.kwargs["severity"] == "warning"
        assert_no_raw_fetch(api)

        await submit(pilot, screen, "")
        assert screen.applied_search == ()
        assert row_ids(screen) == ids(first, second, third)


async def test_live_response_status_enters_and_leaves_applied_view(
    history_app, opened_history
):
    async with opened_history(history_app) as (pilot, screen, api):
        first, second = request(1), request(2)
        deliver(history_app, first, second)
        await submit(pilot, screen, "status:200")
        assert row_ids(screen) == []

        deliver(history_app, response(first, status=200), response(second, status=404))
        await pilot.pause()
        assert row_ids(screen) == ids(first)
        assert screen.http_table.get_cell(str(first.flow_id), "Status").plain == "200"

        deliver(history_app, response(first, status=500), response(second, status=200))
        await pilot.pause()
        assert row_ids(screen) == ids(second)
        assert set(history_app.history_manager.summaries) == {first.flow_id, second.flow_id}
        assert_no_raw_fetch(api)


async def test_live_size_reorders_with_zero_present_and_missing_last(
    history_app, opened_history
):
    async with opened_history(history_app) as (pilot, screen, api):
        missing, large, zero, changing = [request(i) for i in range(1, 5)]
        deliver(history_app, missing, large, zero, changing,
                response(large, size=100), response(zero, size=0),
                response(changing, size=20))
        await pilot.pause()
        screen.http_table.focus()
        await pilot.press("7")
        await pilot.pause()
        assert screen.http_table.active_sort == SortOrder("Size")
        assert row_ids(screen) == ids(zero, changing, large, missing)
        assert screen.http_table.get_cell(str(zero.flow_id), "Size").plain == "0"
        assert screen.http_table.get_cell(str(missing.flow_id), "Size").plain == ""

        deliver(history_app, response(changing, size=200))
        await pilot.pause()
        assert row_ids(screen) == ids(zero, large, changing, missing)
        await pilot.press("7")
        await pilot.pause()
        assert screen.http_table.active_sort == SortOrder("Size", descending=True)
        assert row_ids(screen) == ids(changing, large, zero, missing)

        deliver(history_app, response(changing, size=10))
        await pilot.pause()
        assert row_ids(screen) == ids(large, changing, zero, missing)
        assert_no_raw_fetch(api)


async def test_sort_preserves_selection_details_scope_clears_and_reselection_fetches(
    history_app, opened_history,
):
    async with opened_history(history_app) as (pilot, screen, api):
        selected = request(1, "zeta.test")
        other = request(2, "alpha.test")
        deliver(history_app, selected, other)
        await pilot.pause()
        await select(pilot, screen, selected)
        await screen.workers.wait_for_complete()
        api.raw.get_raw_request.assert_awaited_once_with(selected.flow_id)
        api.raw.get_raw_response.assert_awaited_once_with(selected.flow_id)
        assert screen.request_area.text == "request"
        assert screen.response_area.text == "response"
        api.raw.get_raw_request.reset_mock()
        api.raw.get_raw_response.reset_mock()

        await pilot.press("2")
        await pilot.pause()
        assert row_ids(screen) == ids(other, selected)
        assert screen.http_table.get_highlighted_row_key() == str(selected.flow_id)
        assert screen._selected_summary_uuid == selected.flow_id
        deliver(history_app, response(selected, size=50))
        await pilot.pause()
        assert screen.request_area.text == "request"
        assert screen.response_area.text == "response"
        assert_no_raw_fetch(api)

        api.raw.get_raw_request.return_value = SimpleNamespace(data=b"new request")
        api.raw.get_raw_response.return_value = SimpleNamespace(data=b"new response")
        await pilot.press("enter")
        await pilot.pause()
        await screen.workers.wait_for_complete()
        api.raw.get_raw_request.assert_awaited_once_with(selected.flow_id)
        api.raw.get_raw_response.assert_awaited_once_with(selected.flow_id)
        assert screen.request_area.text == "new request"
        assert screen.response_area.text == "new response"
        api.raw.get_raw_request.reset_mock()
        api.raw.get_raw_response.reset_mock()

        history_app.active_scope = Scope(
            id=1, name="Exclude selected", allow_endpoints=[],
            deny_endpoints=[selected.host],
        )
        await pilot.pause()
        assert row_ids(screen) == ids(other)
        assert screen._selected_summary_uuid is None
        assert screen.request_area.text == ""
        assert screen.response_area.text == ""
        assert_no_raw_fetch(api)
        history_app.active_scope = None
        await pilot.pause()
        assert row_ids(screen) == ids(other, selected)
        assert screen._selected_summary_uuid is None
        assert_no_raw_fetch(api)


@pytest.mark.parametrize("stage", ["request", "response"])
@pytest.mark.parametrize("invalidate", ["search", "project", "api"])
async def test_delayed_raw_result_cannot_overwrite_invalidated_view(
    history_app, opened_history, project_factory, stage, invalidate
):
    async with opened_history(history_app) as (pilot, screen, api):
        summary = request(1)
        deliver(history_app, summary)
        await pilot.pause()
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(_flow_id):
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                # Model an in-flight transport that returns despite cancellation.
                await release.wait()
            return SimpleNamespace(data=b"stale data")

        getattr(api.raw, f"get_raw_{stage}").side_effect = delayed
        try:
            await select(pilot, screen, summary)
            await asyncio.wait_for(started.wait(), timeout=2)
            if invalidate == "search":
                await submit(pilot, screen, "host:excluded.test")
                assert screen._selected_summary_uuid is None
            elif invalidate == "project":
                # Change identity without cancellation to exercise the project guard.
                history_app.active_project = project_factory()
            else:
                history_app.connection_manager._api_client = cast(
                    ApiClient, SimpleNamespace(raw=api.raw)
                )
            screen.request_area.text = "current request"
            screen.response_area.text = "current response"
            release.set()
            await asyncio.wait_for(screen.workers.wait_for_complete(), timeout=2)
            await pilot.pause()
            assert screen.request_area.text == "current request"
            assert screen.response_area.text == "current response"
            if stage == "request":
                api.raw.get_raw_response.assert_not_awaited()
            else:
                api.raw.get_raw_response.assert_awaited_once_with(summary.flow_id)
        finally:
            release.set()


async def test_clear_screen_preserves_view_but_project_switch_resets_it(
    history_app, opened_history, project_factory
):
    async with opened_history(history_app) as (pilot, screen, api):
        summary = request(1)
        deliver(history_app, summary)
        await submit(pilot, screen, "host:example.test")
        await select(pilot, screen, summary)
        await screen.workers.wait_for_complete()
        await pilot.press("7")
        await pilot.pause()
        screen.search_bar.value = "unsubmitted draft"
        screen.clear_screen()
        await pilot.pause()
        assert row_ids(screen) == []
        assert screen.applied_search == parse_search_query("host:example.test")
        assert screen.search_bar.value == "unsubmitted draft"
        assert screen.http_table.active_sort == SortOrder("Size")
        assert screen._selected_summary_uuid is None
        assert screen.request_area.text == screen.response_area.text == ""
        assert summary.flow_id in history_app.history_manager.summaries
        api.summaries.delete_all_flows.assert_not_awaited()

        history_app.set_project(project_factory())
        await pilot.pause()
        await history_app.workers.wait_for_complete()
        await pilot.pause()
        assert screen.applied_search == ()
        assert screen.search_bar.value == ""
        assert screen.http_table.active_sort is None
        assert row_ids(screen) == []
        assert not history_app.history_manager.summaries
        api.summaries.get_all_summaries.assert_awaited_once_with(0, 50)


@pytest.mark.parametrize("confirmed", [False, True])
async def test_delete_all_remains_unfiltered_and_preserves_search_sort(
    history_app, opened_history, confirmed
):
    async with opened_history(history_app) as (pilot, screen, api):
        visible, hidden = request(1, "visible.test"), request(2, "hidden.test")
        deliver(history_app, visible, hidden)
        await submit(pilot, screen, "host:visible.test")
        screen.http_table.focus()
        await pilot.press("7")
        await pilot.pause()
        assert row_ids(screen) == ids(visible)
        screen.action_delete_all_entries()
        await pilot.pause()
        await pilot.click("#confirm-yes" if confirmed else "#confirm-no")
        await pilot.pause()
        api.summaries.delete_flow.assert_not_awaited()
        assert screen.applied_search == parse_search_query("host:visible.test")
        assert screen.search_bar.value == "host:visible.test"
        assert screen.http_table.active_sort == SortOrder("Size")
        if confirmed:
            assert api.summaries.delete_all_flows.await_args_list == [call()]
            assert not history_app.history_manager.summaries
            assert row_ids(screen) == []
        else:
            api.summaries.delete_all_flows.assert_not_awaited()
            assert set(history_app.history_manager.summaries) == {visible.flow_id, hidden.flow_id}
            assert row_ids(screen) == ids(visible)
        assert_no_raw_fetch(api)
