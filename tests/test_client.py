import asyncio
import json
from pathlib import Path

import httpx
import pytest

from sandfish_sdk import OperationError, Sandfish, SandfishError, models

FIXTURE = json.loads((Path(__file__).parents[1] / "testdata/contract.json").read_text())


def test_generated_models_import_and_keep_null_distinct_from_omitted():
    for name in models.__all__:
        getattr(models, name)
    omitted = models.SubmitUrlRequest(url="https://example.com/").to_dict()
    explicit = models.SubmitUrlRequest(url="https://example.com/", visibility=None).to_dict()
    assert "visibility" not in omitted
    assert explicit["visibility"] is None


def test_sync_submission_sends_authentication_and_wire_field_names():
    def handle(request):
        assert str(request.url) == "https://example.test/api/analyses"
        assert request.headers["Authorization"] == "Bearer ak_example"
        assert json.loads(request.content) == {
            "url": "https://example.com/",
            "visibility": "public",
        }
        return httpx.Response(202, json=FIXTURE["accepted"])

    with Sandfish(
        "ak_example", base_url="https://example.test", transport=httpx.MockTransport(handle)
    ) as client:
        result = client.analyses.submit_url_sync(
            models.SubmitUrlRequest(url="https://example.com/", visibility="public")
        )
    assert result.operation_id == FIXTURE["accepted"]["operation_id"]


async def test_async_polling_stops_at_success_and_preserves_null():
    calls = 0

    def handle(request):
        nonlocal calls
        calls += 1
        assert "Authorization" not in request.headers
        operation = dict(FIXTURE["operation"], status="running" if calls == 1 else "succeeded")
        return httpx.Response(200, json=operation)

    async with Sandfish(transport=httpx.MockTransport(handle)) as client:
        result = await client.wait_for_operation(FIXTURE["operation"]["id"], interval=0.001)
    assert calls == 2
    assert result.finished_at is None


@pytest.mark.parametrize("status", ["failed", "cancelled"])
async def test_polling_reports_failed_and_cancelled_operations(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json=dict(FIXTURE["operation"], status=status))
    )
    async with Sandfish(transport=transport) as client:
        with pytest.raises(OperationError) as error:
            await client.wait_for_operation(FIXTURE["operation"]["id"])
    assert error.value.operation.status.value == status


async def test_polling_timeout_cancels_the_request():
    async def handle(_):
        await asyncio.sleep(60)
        raise AssertionError("The request was not cancelled")

    async with Sandfish(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(TimeoutError):
            await client.wait_for_operation(FIXTURE["operation"]["id"], timeout=0.01)


async def test_retries_reads_but_does_not_repeat_submissions():
    methods = []

    def handle(request):
        methods.append(request.method)
        if len(methods) == 2:
            return httpx.Response(200, json=FIXTURE["operation"])
        return httpx.Response(
            429,
            headers={"Retry-After": "0", "X-Request-ID": "request-fixture"},
            json={"error": {"code": "rate_limited", "message": "Wait"}},
        )

    async with Sandfish(transport=httpx.MockTransport(handle)) as client:
        await client.operations.get_operation(FIXTURE["operation"]["id"])
        with pytest.raises(SandfishError) as error:
            await client.analyses.submit_url(models.SubmitUrlRequest(url="https://example.com/"))
    assert methods == ["GET", "GET", "POST"]
    assert error.value.status == 429
    assert error.value.request_id == "request-fixture"


async def test_search_discriminator_selects_the_group_model():
    async with Sandfish(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=FIXTURE["search"]))
    ) as client:
        result = await client.search.search_all(q="example")
    assert isinstance(result.items[0].actual_instance, models.GroupSearchResult)


async def test_pagination_uses_the_returned_limit():
    offsets = []

    def handle(request):
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        return httpx.Response(
            200, json={"items": [FIXTURE["analysis"]], "limit": 1, "offset": offset, "total": 2}
        )

    async with Sandfish(transport=httpx.MockTransport(handle)) as client:
        analyses = [item async for item in client.iter_analyses(limit=10)]
    assert offsets == [0, 1]
    assert len(analyses) == 2
    assert analyses[0].current_evaluation is None


async def test_multipart_upload_contains_file_bytes():
    def handle(request):
        assert request.headers["Content-Type"].startswith("multipart/form-data; boundary=")
        assert b"<html>example</html>" in request.content
        return httpx.Response(202, json=FIXTURE["accepted"])

    async with Sandfish("ak_example", transport=httpx.MockTransport(handle)) as client:
        await client.analyses.submit_wacz(file=b"<html>example</html>", visibility="public")


async def test_streaming_download_and_proxy_error(tmp_path):
    def handle(request):
        if request.url.path.endswith("/screenshot"):
            return httpx.Response(
                200, content=b"\x89PNG\x00\xff", headers={"Content-Type": "image/png"}
            )
        return httpx.Response(
            502, content=b"<html>Proxy error</html>", headers={"X-Request-ID": "proxy-fixture"}
        )

    destination = tmp_path / "screenshot.png"
    async with Sandfish(transport=httpx.MockTransport(handle), max_retries=0) as client:
        await client.download("/api/analyses/example/screenshot", destination)
        with pytest.raises(SandfishError) as error:
            await client.download("/api/analyses/example/wacz", destination)
    assert destination.read_bytes() == b"\x89PNG\x00\xff"
    assert error.value.request_id == "proxy-fixture"
