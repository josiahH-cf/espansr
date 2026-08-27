"""Crash-safe file replacement helpers for Espansr-owned files."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path | str, data: bytes, *, mode: int | None = None) -> None:
    """Write *data* beside *path* and atomically replace the destination.

    Readers therefore observe either the complete previous file or the complete
    replacement. The temporary file is always created on the destination
    filesystem so ``os.replace`` retains its atomic guarantee.
    """

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    inherited_mode = mode
    if inherited_mode is None:
        try:
            inherited_mode = stat.S_IMODE(destination.stat().st_mode)
        except FileNotFoundError:
            inherited_mode = 0o600

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, inherited_mode)
        os.replace(temporary_path, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path | str, value: Any) -> None:
    """Serialize JSON exactly once and atomically replace *path*."""

    atomic_write_bytes(Path(path), json.dumps(value, indent=2).encode("utf-8"))


def atomic_copy(source: Path | str, destination: Path | str) -> None:
    """Copy one complete source snapshot into *destination* atomically."""

    source_path = Path(source)
    source_bytes = source_path.read_bytes()
    source_mode = stat.S_IMODE(source_path.stat().st_mode)
    atomic_write_bytes(Path(destination), source_bytes, mode=source_mode)


def _fsync_directory(directory: Path) -> None:
    """Persist a directory entry where the platform supports directory fsync."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        # Windows and some filesystems reject directory fsync. Replacement is
        # still atomic; only the stronger crash-persistence hint is unavailable.
        pass
    finally:
        os.close(descriptor)
