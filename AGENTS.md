If this checkout lives under `~/JAK` (the owner's workspace), read `~/JAK/AGENTS.md` first (map + floor rules), then `~/JAK/companies/app-studio/AGENTS.md`. Standalone clones can ignore this line.

# ReadEase — agent instructions

macOS app that reads EPUB, PDF and pasted text aloud with local voices (UI in `app/`, Python engine in `src/`).
Overview: `README.md`; change, dependency and release rules: `CONTRIBUTING.md` (read it before editing).

- Add a failing test before changing behaviour, then run the narrow test and `./scripts/verify.sh`.
- Visible changes: `cd app && pnpm dev`, then `pnpm audit:render` in another terminal.
- `main` requires CI: work on a branch and open a pull request.
- `uv.lock` is the dependency source of truth; never commit models, books, databases or user data.
