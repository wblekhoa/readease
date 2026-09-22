#!/usr/bin/env python3
"""Serve the built landing. Run npm ci && npm run build in site/ first."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "dist"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def end_headers(self):
        # Local preview must show edits, not a previous CSS/JS response.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    if not (SITE / "index.html").is_file():
        parser.error("Build first: npm ci --prefix site && npm run build --prefix site")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ReadEase preview: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
