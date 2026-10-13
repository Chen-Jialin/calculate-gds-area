"""Load the tested KLayout wheel or automatically obtain an isolated uv environment."""
from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
from i18n import LocalizedError, language_from_args, text

KLAYOUT_VERSION = "0.30.12"


def compatible() -> bool:
    try:
        import klayout.db  # noqa: F401
        return importlib.metadata.version("klayout") == KLAYOUT_VERSION
    except (ImportError, OSError, importlib.metadata.PackageNotFoundError):
        return False


def ensure_runtime(language=None) -> None:
    language = language or language_from_args()
    if compatible():
        return
    if os.environ.get("GDS_AREA_BOOTSTRAPPED") == "1":
        raise LocalizedError("runtime_failed")
    entrypoint = Path(sys.argv[0]).name
    if entrypoint not in ("gds_area.py", "self_test.py"):
        raise LocalizedError("runtime_entrypoint")
    folder = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["GDS_AREA_BOOTSTRAPPED"] = "1"
    env["GDS_AREA_MANAGED_PYTHON"] = "1"
    env["GDS_AREA_ENTRYPOINT"] = entrypoint
    env["GDS_AREA_LANG"] = language
    env["PYTHONIOENCODING"] = "utf-8"
    # uv can build its environment from an existing interpreter without pip or
    # ensurepip; obtain managed Python 3.12 only when explicitly requested/needed.
    if os.environ.get("GDS_AREA_MANAGED_PYTHON") != "1" and (3, 10) <= sys.version_info[:2] < (3, 15):
        env["GDS_AREA_UV_PYTHON"] = sys.executable
    print(text("runtime_install", language, version=KLAYOUT_VERSION), file=sys.stderr)
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            raise LocalizedError("need_powershell")
        command = [shell, "-NoProfile", "-File", str(folder / "run.ps1")]
    else:
        command = ["sh", str(folder / "run.sh")]
    raise SystemExit(subprocess.call([*command, *sys.argv[1:]], env=env))
