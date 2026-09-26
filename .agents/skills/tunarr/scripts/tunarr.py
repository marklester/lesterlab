"""Entry point for the Tunarr CLI.

Run from the ``scripts/`` directory after ``uv sync``:

    .venv/bin/python tunarr.py <command>

or use the installed console script:

    .venv/bin/tunarr <command>

The CLI implementation lives in the ``tunarr_cli`` package next to this
file.
"""

from tunarr_cli.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
