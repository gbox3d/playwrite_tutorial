from __future__ import annotations

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
PLAYWRIGHT_DIR = ROOT_DIR / ".playwright"
LEGACY_SYSTEM_FILE = ROOT_DIR / "temp" / "system.yaml"
DEFAULT_SYSTEM_FILE = PLAYWRIGHT_DIR / "system.yaml"

_system_file: Path = DEFAULT_SYSTEM_FILE


def set_system_file(path: Path) -> None:
    global _system_file
    _system_file = path


def get_system_file() -> Path:
    if _system_file != DEFAULT_SYSTEM_FILE:
        return _system_file
    if DEFAULT_SYSTEM_FILE.exists() or not LEGACY_SYSTEM_FILE.exists():
        return DEFAULT_SYSTEM_FILE
    return LEGACY_SYSTEM_FILE


def load_macros() -> dict[str, list[str]]:
    path = get_system_file()
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}

    if not isinstance(data, dict) or not isinstance(data.get("macros"), dict):
        return {}

    macros: dict[str, list[str]] = {}
    for name, value in data["macros"].items():
        commands = _normalize_macro_value(value)
        if commands is not None:
            macros[str(name)] = commands
    return macros


def load_macro(name: str) -> list[str] | None:
    return load_macros().get(name)


def _normalize_macro_value(value: object) -> list[str] | None:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]

    if isinstance(value, dict) and isinstance(value.get("commands"), list):
        return [item for item in value["commands"] if isinstance(item, str)]

    return None
