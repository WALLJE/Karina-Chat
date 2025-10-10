"""Persistente Speicherung des Fall- und Verhaltens-Fixierungszustands."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Tuple

__all__ = [
    "get_fall_fix_state",
    "set_fixed_scenario",
    "clear_fixed_scenario",
    "get_behavior_fix_state",
    "set_fixed_behavior",
    "clear_fixed_behavior",
]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_CONFIG_PATH = _DATA_DIR / "fall_config.json"

_LOCK = Lock()
_MAX_FIX_DURATION = timedelta(hours=4)


def _default_section() -> Dict[str, Any]:
    return {"fixed": False, "value": "", "timestamp": None}


def _default_config() -> Dict[str, Dict[str, Any]]:
    return {"scenario": _default_section(), "behavior": _default_section()}


def _sanitize_section(section: Any) -> Dict[str, Any]:
    if not isinstance(section, dict):
        return _default_section()
    timestamp = section.get("timestamp")
    if isinstance(timestamp, str):
        timestamp_value: str | None = timestamp
    else:
        timestamp_value = None
    return {
        "fixed": bool(section.get("fixed", False)),
        "value": str(section.get("value", "")),
        "timestamp": timestamp_value,
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _section_expired(section: Dict[str, Any]) -> bool:
    timestamp = section.get("timestamp")
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False
    return datetime.now(timezone.utc) - parsed > _MAX_FIX_DURATION


def _load_config() -> Dict[str, Dict[str, Any]]:
    with _LOCK:
        if not _CONFIG_PATH.exists():
            return _default_config()
        try:
            raw = _CONFIG_PATH.read_text(encoding="utf-8")
        except OSError:
            return _default_config()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        default_config = _default_config()
        _save_config(default_config)
        return default_config

    config = _default_config()
    if not isinstance(data, dict):
        return config

    scenario_section = data.get("scenario")
    behavior_section = data.get("behavior")

    if isinstance(scenario_section, dict):
        config["scenario"] = _sanitize_section(scenario_section)
    else:
        config["scenario"] = _sanitize_section(
            {
                "fixed": data.get("fixed", False),
                "value": data.get("scenario", ""),
                "timestamp": data.get("timestamp"),
            }
        )

    if isinstance(behavior_section, dict):
        config["behavior"] = _sanitize_section(behavior_section)
    else:
        config["behavior"] = _sanitize_section(
            {
                "fixed": data.get("behavior_fixed", False),
                "value": data.get("behavior", ""),
                "timestamp": data.get("behavior_timestamp"),
            }
        )

    return config


def _save_config(data: Dict[str, Dict[str, Any]]) -> None:
    serializable = {
        "scenario": _sanitize_section(data.get("scenario")),
        "behavior": _sanitize_section(data.get("behavior")),
    }
    with _LOCK:
        try:
            _CONFIG_PATH.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass


def get_fall_fix_state() -> Tuple[bool, str]:
    """Gibt zurück, ob ein Szenario fixiert ist und welches Szenario gesetzt wurde."""

    data = _load_config()
    scenario_section = data["scenario"]
    if scenario_section["fixed"]:
        if _section_expired(scenario_section) or not scenario_section["value"].strip():
            data["scenario"] = _default_section()
            _save_config(data)
            return False, ""
        return True, scenario_section["value"]
    return False, ""


def set_fixed_scenario(szenario: str) -> None:
    """Aktiviert die Fall-Fixierung für das angegebene Szenario."""

    scenario_value = str(szenario).strip()
    data = _load_config()
    data["scenario"] = {
        "fixed": True,
        "value": scenario_value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _save_config(data)


def clear_fixed_scenario() -> None:
    """Deaktiviert die Fall-Fixierung und entfernt das gespeicherte Szenario."""

    data = _load_config()
    data["scenario"] = _default_section()
    _save_config(data)


def get_behavior_fix_state() -> Tuple[bool, str]:
    """Gibt zurück, ob ein Verhalten fixiert ist und welches Verhalten gesetzt wurde."""

    data = _load_config()
    behavior_section = data["behavior"]
    if behavior_section["fixed"]:
        if _section_expired(behavior_section) or not behavior_section["value"].strip():
            data["behavior"] = _default_section()
            _save_config(data)
            return False, ""
        return True, behavior_section["value"]
    return False, ""


def set_fixed_behavior(verhalten: str) -> None:
    """Aktiviert die Fixierung für die übergebene Verhaltensoption."""

    behavior_value = str(verhalten).strip()
    data = _load_config()
    data["behavior"] = {
        "fixed": True,
        "value": behavior_value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _save_config(data)


def clear_fixed_behavior() -> None:
    """Deaktiviert die Fixierung der Verhaltensoption."""

    data = _load_config()
    data["behavior"] = _default_section()
    _save_config(data)
