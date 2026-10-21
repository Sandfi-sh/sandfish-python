# Agent instructions

Read [README.md](README.md) for the client interface and local checks.
Read the [SDK maintenance guide](https://github.com/Sandfi-sh/openapi/blob/main/MAINTAINING.md)
for cross-repository work and the
[release guide](https://github.com/Sandfi-sh/openapi/blob/main/RELEASING.md)
for PyPI publication.

- Check the working tree, remote revision, and unpublished commits first.
- Change API methods and models through `sandfi-sh/openapi`, then regenerate.
- Keep generated files inside `src/sandfish_sdk/generated`.
- Preserve the maintained initializer, `client.py`, and `py.typed`.
- Preserve async methods and typed `_sync` methods. Test the affected mode.
- Use PyPI name `sandfish-sdk` and import name `sandfish_sdk`.
- Keep `sdk.json`, package metadata, and generated version metadata consistent.
- Run the README checks for code changes. Verify an installed wheel for releases.
- Check links, references, commands, and `git diff --check` for prose changes.
- Keep credentials out of Git, documentation, and tool output.
- Update the owning guide and report local, published, and verified state.

Use short, direct sentences, active voice, and consistent technical terms.
