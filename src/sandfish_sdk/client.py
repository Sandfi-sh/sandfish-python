"""Client configuration, polling, pagination, and streaming downloads."""

from __future__ import annotations

import asyncio
import json
import math
import os
import tempfile
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from sandfish_sdk.generated.api import (
    ActorsApi,
    AnalysesApi,
    AnalysisGroupsApi,
    BehaviorEventsApi,
    BrandsApi,
    EmailAnalysesApi,
    ExecutionProfilesApi,
    FaviconsApi,
    IdentifiersApi,
    InfrastructureApi,
    InteractionsApi,
    JavascriptFunctionsApi,
    OperationsApi,
    PayloadsApi,
    PhishingKitsApi,
    RequestsApi,
    RulesApi,
    SearchApi,
    SignalsApi,
    StatsApi,
    TlsCertificatesApi,
    UsageApi,
)
from sandfish_sdk.generated.api_client import ApiClient
from sandfish_sdk.generated.configuration import Configuration
from sandfish_sdk.generated.models.analysis_summary import AnalysisSummary
from sandfish_sdk.generated.models.operation_out import OperationOut
from sandfish_sdk.generated.sync_helper import run_sync


class SandfishError(Exception):
    """An API or proxy error with its HTTP status and request identifier."""

    def __init__(self, status: int, body: bytes, headers: httpx.Headers):
        self.status = status
        self.request_id = headers.get("X-Request-ID")
        self.retry_after = headers.get("Retry-After")
        self.code = "http_error"
        self.details: Any = None
        self.body = body
        message = f"Sandfish returned HTTP {status}"
        try:
            error = json.loads(body)["error"]
            if isinstance(error.get("message"), str):
                message = error["message"]
            self.code = error.get("code", self.code)
            self.details = error.get("details")
            self.request_id = error.get("request_id") or self.request_id
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
        super().__init__(message)


class OperationError(Exception):
    """An operation reached a failed or cancelled terminal state."""

    def __init__(self, operation: OperationOut):
        self.operation = operation
        super().__init__(f"Operation {operation.id} {operation.status.value}")


def _retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            seconds = float(value)
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                seconds = (date - datetime.now(UTC)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                seconds = -1
        if math.isfinite(seconds) and seconds >= 0:
            return seconds
    return min(2**attempt, 30)


class _Client(ApiClient):
    def __init__(self, configuration, http_client, timeout, max_retries):
        super().__init__(configuration)
        self.rest_client.pool_manager = http_client
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = f"sandfish-python/{version('sandfish-sdk')}"

    async def call_api(
        self, method, url, header_params=None, body=None, post_params=None, _request_timeout=None
    ):
        for attempt in range(self.max_retries + 1):
            response = await super().call_api(
                method,
                url,
                header_params,
                body,
                post_params,
                _request_timeout if _request_timeout is not None else self.timeout,
            )
            if (
                method in {"GET", "HEAD"}
                and response.status in {429, 502, 503, 504}
                and attempt < self.max_retries
            ):
                delay = _retry_delay(response.headers.get("Retry-After"), attempt)
                await response.response.aclose()
                await asyncio.sleep(delay)
                continue
            if response.status >= 400:
                raise SandfishError(response.status, await response.read(), response.headers)
            return response
        raise AssertionError("Retry loop did not return a response")


class Sandfish:
    """Use generated async methods or their typed `_sync` variants."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://sandfi.sh",
        timeout: float = 30,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        url = urlsplit(base_url)
        if url.scheme not in {"http", "https"} or not url.netloc or url.query or url.fragment:
            raise ValueError("base_url must be an HTTP server URL")
        if url.path.rstrip("/").endswith("/api"):
            raise ValueError("base_url must omit /api; generated paths already include it")
        if timeout <= 0 or max_retries < 0:
            raise ValueError("timeout must be positive and max_retries must be nonnegative")
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.AsyncClient(transport=transport, timeout=timeout)
        self._api = _Client(
            Configuration(host=self.base_url, access_token=api_key),
            self._http,
            timeout,
            max_retries,
        )
        self.actors = ActorsApi(self._api)
        self.analyses = AnalysesApi(self._api)
        self.analysis_groups = AnalysisGroupsApi(self._api)
        self.behavior_events = BehaviorEventsApi(self._api)
        self.brands = BrandsApi(self._api)
        self.email_analyses = EmailAnalysesApi(self._api)
        self.execution_profiles = ExecutionProfilesApi(self._api)
        self.favicons = FaviconsApi(self._api)
        self.identifiers = IdentifiersApi(self._api)
        self.infrastructure = InfrastructureApi(self._api)
        self.interactions = InteractionsApi(self._api)
        self.javascript_functions = JavascriptFunctionsApi(self._api)
        self.operations = OperationsApi(self._api)
        self.payloads = PayloadsApi(self._api)
        self.phishing_kits = PhishingKitsApi(self._api)
        self.requests = RequestsApi(self._api)
        self.rules = RulesApi(self._api)
        self.search = SearchApi(self._api)
        self.signals = SignalsApi(self._api)
        self.stats = StatsApi(self._api)
        self.tls_certificates = TlsCertificatesApi(self._api)
        self.usage = UsageApi(self._api)

    async def close(self) -> None:
        await self._api.close()

    def close_sync(self) -> None:
        run_sync(self.close())

    async def __aenter__(self) -> Sandfish:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def __enter__(self) -> Sandfish:
        return self

    def __exit__(self, *args) -> None:
        self.close_sync()

    async def wait_for_operation(
        self, operation_id: str, *, timeout: float = 300, interval: float = 1
    ) -> OperationOut:
        if timeout <= 0 or interval <= 0:
            raise ValueError("timeout and interval must be positive")
        async with asyncio.timeout(timeout):
            while True:
                operation = await self.operations.get_operation(operation_id)
                if operation.status.value == "succeeded":
                    return operation
                if operation.status.value in {"failed", "cancelled"}:
                    raise OperationError(operation)
                await asyncio.sleep(interval)

    def wait_for_operation_sync(
        self, operation_id: str, *, timeout: float = 300, interval: float = 1
    ) -> OperationOut:
        return run_sync(self.wait_for_operation(operation_id, timeout=timeout, interval=interval))

    async def iter_analyses(
        self, *, limit: int = 50, **filters: Any
    ) -> AsyncIterator[AnalysisSummary]:
        offset = filters.pop("offset", 0)
        while True:
            page = await self.analyses.list_analyses(limit=limit, offset=offset, **filters)
            for item in page.items:
                yield item
            if not page.items or page.offset + page.limit >= page.total:
                return
            if page.limit <= 0 or page.offset + page.limit <= offset:
                raise ValueError("The API returned a non-advancing page")
            offset = page.offset + page.limit

    def iter_analyses_sync(self, *, limit: int = 50, **filters: Any) -> Iterator[AnalysisSummary]:
        iterator = self.iter_analyses(limit=limit, **filters)
        try:
            while True:
                try:
                    yield run_sync(anext(iterator))
                except StopAsyncIteration:
                    return
        finally:
            run_sync(iterator.aclose())

    async def download(self, api_path: str, destination: str | Path) -> Path:
        """Stream an API download to a file and replace it only after completion."""
        if not api_path.startswith("/api/") or urlsplit(api_path).netloc:
            raise ValueError("api_path must start with /api/")
        destination = Path(destination)
        temporary: Path | None = None
        try:
            async with self._http.stream(
                "GET", self.base_url + api_path, headers=self._headers
            ) as response:
                if not response.is_success:
                    raise SandfishError(
                        response.status_code, await response.aread(), response.headers
                    )
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                    temporary = Path(output.name)
                    async for chunk in response.aiter_bytes():
                        output.write(chunk)
                os.replace(temporary, destination)
                temporary = None
            return destination
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def download_sync(self, api_path: str, destination: str | Path) -> Path:
        return run_sync(self.download(api_path, destination))
