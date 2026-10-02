"""Entry script used by PyInstaller (a packaged app needs a plain script, not -m)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from khanyo_toolkit.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
