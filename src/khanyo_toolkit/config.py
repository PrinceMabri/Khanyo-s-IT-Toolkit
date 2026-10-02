"""Application-wide constants and settings."""

import os
import platform

from . import __version__

APP_NAME = "Khanyo IT Toolkit"
APP_TITLE = f"{APP_NAME} V{'.'.join(__version__.split('.')[:2])}"
IS_WINDOWS = platform.system() == "Windows"

# Where support reports are saved by default. Override with the
# KHANYO_REPORTS_DIR environment variable.
REPORTS_DIR = os.environ.get("KHANYO_REPORTS_DIR") or os.path.join(
    os.path.expanduser("~"), "Documents", "Khanyo Reports"
)
