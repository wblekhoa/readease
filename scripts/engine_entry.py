"""PyInstaller entry for the packaged reading engine."""
from vieneu_reader.headless.server import main

if __name__ == "__main__":
    raise SystemExit(main())
