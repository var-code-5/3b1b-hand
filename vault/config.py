# src/my_agentic_app/config.py
from pathlib import Path
import platform
import os


def get_app_data_dir() -> Path:
    """
    Get cross-platform app data directory.
    Windows: %APPDATA%\threeb1b
    macOS: ~/Library/Application Support/threeb1b
    Linux: ~/.local/share/threeb1b
    """

    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux and others
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "threeb1b"
    return app_dir


# App paths
# Allow overriding the vault file location via environment variable for
# flexibility (useful for tests or custom deployments). If VAULT_FILE is set
# we use its parent as the application data directory.
_env_vault = os.environ.get("VAULT_FILE")
if _env_vault:
    VAULT_FILE = Path(_env_vault).expanduser()
    APP_DATA_DIR = VAULT_FILE.parent
else:
    APP_DATA_DIR = get_app_data_dir()
    VAULT_FILE = APP_DATA_DIR / "vault.enc"

LOG_DIR = APP_DATA_DIR / "logs"
CONFIG_DIR = APP_DATA_DIR / "config"


def ensure_directories():
    """Create necessary directories on startup.

    If a custom VAULT_FILE path is provided via env var, ensure its parent
    directory exists so the vault can be created there.
    """
    for directory in [APP_DATA_DIR, LOG_DIR, CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Ensure dirs exist on import
ensure_directories()
