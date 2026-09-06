"""Helpers shared by the orchestratr connector and manifest-schema tests.

Not a test module (no ``test_`` prefix), so pytest never collects it.
"""

import json
import types
from pathlib import Path


def _make_config_env(tmp_path: Path, *, templates: int = 1, espanso: bool = True):
    """Set up a fake espansr config directory with optional templates and espanso.

    Returns (config_dir, templates_dir, espanso_dir_or_none).
    """
    config_dir = tmp_path / "espansr"
    config_dir.mkdir(parents=True)
    templates_dir = config_dir / "templates"
    templates_dir.mkdir()

    for i in range(templates):
        (templates_dir / f"tmpl_{i}.json").write_text(
            json.dumps(
                {
                    "name": f"Template {i}",
                    "trigger": f":t{i}",
                    "content": f"Content {i}",
                }
            )
        )

    espanso_dir = None
    if espanso:
        espanso_dir = tmp_path / "espanso"
        espanso_dir.mkdir()

    return config_dir, templates_dir, espanso_dir


def _make_bundled_dir(tmp_path: Path) -> Path:
    """Create a fake bundled starter directory for cmd_setup tests."""
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()
    (bundled_dir / "starter.json").write_text(
        json.dumps({"name": "Starter", "trigger": ":starter", "content": "Starter"})
    )
    return bundled_dir


def _make_args(**kwargs):
    """Create a simple namespace to simulate argparse output."""
    return types.SimpleNamespace(**kwargs)


def _make_config_stub(last_sync: str = ""):
    """Create a minimal config stub with espanso.last_sync set."""
    espanso = types.SimpleNamespace(last_sync=last_sync)
    return types.SimpleNamespace(espanso=espanso)
