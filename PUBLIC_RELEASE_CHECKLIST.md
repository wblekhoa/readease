# Public release checklist

## Small-circle source sharing

- Run `scripts/export-public-source.py` to create a clean source folder and ZIP;
  never share this workspace checkout or its history.
- The recipient can Control-click **Install ReadEase.command** and choose
  **Open**, or ask an AI assistant to run that file. The installer must pass its
  Apple Silicon, macOS 15, disk-space, Xcode-tools, checksum, locked-build,
  whole-bundle compatibility, signing-integrity, and launch gates.
- This path is a local self-build for friends. It does not turn the ad-hoc
  signed app into a public downloadable binary and does not replace Developer
  ID/notarization or a final legal review.

## Source repository

- Create a new repository from one clean, allowlisted squash export. Do not
  push this workspace's existing history, internal `ai-memory`, build archives,
  or local planning documents.
- Include only source, tests, build scripts, branding assets, public guides,
  `uv.lock`, and the `legal` directory checked by
  `scripts/audit-public-release.py --strict`.
- Never include model weights, books, PDF/EPUB samples with uncertain rights,
  database files, audio cache, `.env`, credentials, user paths, or personal
  email metadata.
- Describe the repository as source-available for noncommercial use, not open
  source. Require the unmodified PolyForm Noncommercial 1.0.0 `LICENSE`, the
  current source-matching `NOTICE.md`, and provenance marker in the source and
  every distributed app.
- State clearly that commercial use of the ReadEase-owned scaffold requires a
  separate written license and that third-party/model licenses are unchanged.
- Configure GitHub Security Advisories before making the repository public.

## Binary candidate

- Build once from the clean checkout and locked environment.
- Verify the fresh Nuitka report contains neither PyMuPDF nor excluded cloning
  dependencies, and the bundle contains QtPdf but no Qt Virtual Keyboard.
- Require the generated `Contents/Resources/Legal` payload and matching report
  hash, plus matching provenance in `Info.plist` and
  `Contents/Resources/Provenance/READEASE_PROVENANCE.json`.
- Run `scripts/audit-public-release.py --strict --bundle ... --report ...`.
- Complete Developer ID signing, notarization, trademark review, model/voice
  provenance review, and LGPL corresponding-source/relink review.

Creating the GitHub repository, publishing a Release, and notarization are
external actions and require the publisher's explicit approval.
