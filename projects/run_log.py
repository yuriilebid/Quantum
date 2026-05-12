"""Mirror stdout/stderr to a UTF-8 text file (used by demo CLIs)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TextIO

_state: dict[str, Any] | None = None


class _Tee(TextIO):
    def __init__(self, stream: TextIO, log_fp: TextIO) -> None:
        object.__setattr__(self, "_stream", stream)
        object.__setattr__(self, "_log_fp", log_fp)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def write(self, s: str) -> int:
        self._stream.write(s)
        self._log_fp.write(s)
        self._stream.flush()
        self._log_fp.flush()
        return len(s)

    def flush(self) -> None:
        self._stream.flush()
        self._log_fp.flush()


def install(path: str | Path) -> None:
    global _state
    if _state is not None:
        raise RuntimeError("stdio log already installed")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fp = p.open("w", encoding="utf-8")
    orig_out, orig_err = sys.stdout, sys.stderr
    _state = {"fp": fp, "orig_out": orig_out, "orig_err": orig_err}
    sys.stdout = _Tee(orig_out, fp)  # type: ignore[assignment]
    sys.stderr = _Tee(orig_err, fp)  # type: ignore[assignment]


def uninstall() -> None:
    global _state
    if _state is None:
        return
    sys.stdout = _state["orig_out"]
    sys.stderr = _state["orig_err"]
    _state["fp"].close()
    _state = None
