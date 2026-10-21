# Sandfish Python SDK

The official Python client for the [Sandfish API](https://sandfi.sh/docs#api).
Analyze URLs, HTML files, WACZ archives, and EML messages. Follow operations and
inspect evidence through typed models.

**Preview:** the PyPI package name is `sandfish-sdk`. Initial registry
publication is pending. Python 3.11 or later is required.

## Install from GitHub

```sh
python -m pip install git+https://github.com/sandfi-sh/sandfish-python.git
```

Create an API key at <https://sandfi.sh/account/api>. Set `SANDFISH_API_KEY` in
your environment before running authenticated examples.

## Submit and wait

```python
import os
from sandfish_sdk import Sandfish, models

with Sandfish(os.environ["SANDFISH_API_KEY"]) as client:
    accepted = client.analyses.submit_url_sync(
        models.SubmitUrlRequest(url="https://example.com/", visibility="public")
    )
    client.wait_for_operation_sync(accepted.operation_id, timeout=300)
    analysis = client.analyses.get_analysis_sync(accepted.id)
    print(analysis.current_evaluation)
```

Generated methods ending in `_sync` run synchronously. Use the same method
without `_sync` in asynchronous code:

```python
async with Sandfish(api_key) as client:
    accepted = await client.analyses.submit_url(
        models.SubmitUrlRequest(url="https://example.com/", visibility="public")
    )
    await client.wait_for_operation(accepted.operation_id)
```

Use each client instance in one mode. Close it with `with` or `async with`.

## Pagination, uploads, and downloads

```python
with Sandfish(api_key) as client:
    for analysis in client.iter_analyses_sync(limit=50):
        print(analysis.id, analysis.status)

    accepted = client.analyses.submit_wacz_sync(file="sample.html", visibility="public")
    client.wait_for_operation_sync(accepted.operation_id)
    client.download_sync(f"/api/analyses/{accepted.id}/screenshot", "screenshot.png")
```

`submit_wacz` accepts HTML and WACZ files. `analysis_groups.submit_eml` accepts
EML files. Asynchronous pagination uses `async for` with `iter_analyses`.
The download helper streams to a temporary file, then replaces the destination
after completion. Generated download methods can buffer a full response.

## Configuration and errors

`Sandfish(api_key=None, base_url="https://sandfi.sh", timeout=30, max_retries=2)`
configures access. Omit the key for public reads. The server URL must omit `/api`.
HTTPX transports can be supplied for tests or custom connections.

Reads retry HTTP 429, 502, 503, and 504. Retries respect `Retry-After`.
Submissions are sent once. Set `max_retries=0` to disable read retries.
Use a polling timeout to bound all polling requests and retry delays.

`SandfishError` exposes `status`, `code`, `details`, `request_id`, and
`retry_after`. It also handles non-JSON proxy errors. `OperationError` retains a
failed or cancelled operation. Async cancellation follows normal asyncio behavior.

An accepted submission is not a completed analysis. A completed operation is
not a verdict. Read `current_evaluation`, which can be null, and inspect its
completeness and supporting evidence.

## Development

```sh
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv build
```

Endpoint methods and models in `src/sandfish_sdk/generated` are generated.
The [generation guide](https://github.com/sandfi-sh/openapi) owns updates.
`.sdk-generated.json` records source hashes and generated file ownership.
Read the [maintenance guide](https://github.com/Sandfi-sh/openapi/blob/main/MAINTAINING.md)
for change ownership and the
[release guide](https://github.com/Sandfi-sh/openapi/blob/main/RELEASING.md)
for PyPI publication.

[Examples](https://github.com/sandfi-sh/examples) ·
[API documentation](https://sandfi.sh/docs#api) ·
[Report a problem](https://github.com/sandfi-sh/sandfish-python/issues)

## License

MIT. See [LICENSE](LICENSE).
