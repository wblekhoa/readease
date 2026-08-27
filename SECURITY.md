# Security policy

## Supported version

Security fixes target the latest source revision and the latest published
ReadEase release. This repository does not promise fixes for unsigned local
development bundles or modified third-party model files.

## Reporting a vulnerability

After the public repository is created, report vulnerabilities through its
private GitHub Security Advisory form. Do not include book content, selected
text, clipboard data, model weights, API credentials, or other personal data in
a public issue. Until that channel exists, public release remains held rather
than publishing an unsecured contact address.

Useful non-sensitive evidence includes the ReadEase version, macOS version,
reproduction steps with a synthetic document, and whether the issue affects PDF,
EPUB, pasted text, Apple Books selection, model preparation, or packaging.

## Supply-chain boundary

Python packages are locked in `uv.lock`. Runtime model and codec downloads are
pinned to full revisions and are not embedded in the repository. A release
candidate must pass the strict source, bundle, license-manifest, and signing
audits described in `legal/BINARY_DISTRIBUTION.md`.
