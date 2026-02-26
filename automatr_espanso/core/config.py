"""Configuration management for automatr-espanso.

Handles loading/saving app configuration from a single JSON file.
"""

import json
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


def get_platform() -> str:
    """Get the current platform.

    Returns:
        'windows', 'linux', 'wsl2', or 'macos'
    """
    system = platform.system()

    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        # Check for WSL2
        try:
            with open("/proc/version", "r") as f:
                version = f.read().lower()
                if "microsoft" in version or "wsl" in version:
                    return "wsl2"
        except (OSError, IOError):
            pass
        return "linux"
    return "unknown"


def is_windows() -> bool:
    """Check if running on native Windows."""
    return get_platform() == "windows"


def get_config_dir() -> Path:
    """Get the configuration directory path.

    On macOS: ~/Library/Application Support/automatr-espanso
    On Linux/WSL: XDG_CONFIG_HOME or ~/.config/automatr-espanso
    """
    import os

    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"

    config_dir = base / "automatr-espanso"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.json"


def get_templates_dir() -> Path:
    """Get the templates directory path."""
    templates_dir = get_config_dir() / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


@dataclass
class EspansoConfig:
    """Configuration for Espanso integration."""

    config_path: str = ""  # Override for Espanso config dir (empty = auto-detect)
    auto_sync: bool = False
    last_sync: str = ""  # ISO timestamp of last successful sync


@dataclass
class UIConfig:
    """Configuration for the UI."""

    theme: str = "dark"
    window_width: int = 960
    window_height: int = 700
    font_size: int = 13  # Base font size for text content

    # Window state persistence
    window_x: int = -1  # -1 = center on screen
    window_y: int = -1
    window_maximized: bool = False
    window_geometry: str = ""  # Base64 encoded QByteArray

    # Layout persistence
    splitter_sizes: list = field(default_factory=lambda: [300, 660])

    # Selection persistence
    last_template: str = ""
    expanded_folders: list = field(default_factory=list)

    # Template versioning
    max_template_versions: int = 10


@dataclass
class Config:
    """Main application configuration."""

    espanso: EspansoConfig = field(default_factory=EspansoConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create config from dictionary."""
        espanso_data = data.get("espanso", {})
        ui_data = data.get("ui", {})

        # Guard against unknown fields from future versions
        known_espanso = {f.name for f in EspansoConfig.__dataclass_fields__.values()}
        known_ui = {f.name for f in UIConfig.__dataclass_fields__.values()}

        return cls(
            espanso=EspansoConfig(**{k: v for k, v in espanso_data.items() if k in known_espanso})
            if espanso_data
            else EspansoConfig(),
            ui=UIConfig(**{k: v for k, v in ui_data.items() if k in known_ui})
            if ui_data
            else UIConfig(),
        )


class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigManager.

        Args:
            config_path: Path to config file. Uses default if None.
        """
        self.config_path = config_path or get_config_path()
        self._config: Optional[Config] = None

    @property
    def config(self) -> Config:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Config object (defaults if file doesn't exist).
        """
        if not self.config_path.exists():
            return Config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load config: {e}")
            return Config()

    def save(self, config: Optional[Config] = None) -> bool:
        """Save configuration to file.

        Args:
            config: Config to save. Uses current config if None.

        Returns:
            True if saved successfully, False otherwise.
        """
        if config is None:
            config = self.config

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
            self._config = config
            return True
        except OSError as e:
            print(f"Error: Failed to save config: {e}")
            return False

    def update(self, **kwargs) -> bool:
        """Update specific config values and save.

        Supports nested keys like 'espanso.config_path'.

        Args:
            **kwargs: Key-value pairs to update.

        Returns:
            True if saved successfully, False otherwise.
        """
        config = self.config

        for key, value in kwargs.items():
            parts = key.split(".")
            if len(parts) == 2:
                section, attr = parts
                if hasattr(config, section):
                    section_obj = getattr(config, section)
                    if hasattr(section_obj, attr):
                        setattr(section_obj, attr, value)
            elif len(parts) == 1:
                if hasattr(config, key):
                    setattr(config, key, value)

        return self.save(config)


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    """Get the current configuration."""
    return get_config_manager().config


def save_config(config: Optional[Config] = None) -> bool:
    """Save the configuration to file.

    Args:
        config: Config to save. Uses current config if None.

    Returns:
        True if saved successfully, False otherwise.
    """
    return get_config_manager().save(config)
