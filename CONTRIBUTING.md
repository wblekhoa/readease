# Contributing to ReadEase

ReadEase is a Vietnamese-first, local macOS reading app. Keep changes scoped,
preserve users' existing library data, and avoid adding background services,
telemetry, API keys, model weights, copyrighted books, or generated audio.

## Local setup

Use Apple Silicon macOS 15 or later. Keep the build on the managed Python 3.13
selected by `uv`:

```bash
uv sync --locked --managed-python --python 3.13
./scripts/verify.sh
```

`uv.lock` is the dependency source of truth. Adding or upgrading a dependency
requires an explicit license, size, offline-behavior, and bundle-impact review.
PDF support must continue to use QtPdf rather than adding a second PDF engine.

## Change quality

- Add a failing test before changing behavior, then run the narrow test and the
  full verification script.
- Keep model and book fixtures small; never commit `.onnx`, PDF/EPUB books,
  databases, cache files, or user data.
- For packaging changes, produce a fresh Nuitka report and run the strict
  public-release audit against the built app.
- Do not claim a public binary is ready from an ad-hoc signature. Developer ID,
  notarization, license review, and a clean export are separate release gates.

Contributions are accepted under the repository's
`PolyForm-Noncommercial-1.0.0` license. By submitting a contribution, you
represent that you have the right to provide it under those terms. The project
does not currently use a contributor assignment agreement, so maintainers must
not assume they can commercially relicense a contributor's independent work.
