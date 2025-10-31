"""Persistente Verwaltung der ChatGPT+AMBOSS-Funktion."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Tuple

import streamlit as st

__all__ = [
    "PERSISTENCE_DURATION",
    "SESSION_STATE_KEY",
    "activate_chatgpt_amboss",
    "deactivate_chatgpt_amboss",
    "get_chatgpt_amboss_state",
    "is_chatgpt_amboss_active",
    "sync_chatgpt_amboss_session_state",
]

# Die Aktivierung soll standardmäßig zwei Tage gültig bleiben.
PERSISTENCE_DURATION: timedelta = timedelta(days=2)
SESSION_STATE_KEY: str = "chatgpt_amboss_active"

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_CONFIG_PATH = _DATA_DIR / "chatgpt_amboss_config.json"

_LOCK = Lock()
_DEFAULT_CONFIG: Dict[str, Any] = {"enabled": False, "activated_at": None}


def _format_timestamp(moment: datetime | None) -> str | None:
    """Gibt einen ISO-8601-String für den Speicher zurück."""

    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_timestamp(raw: Any) -> datetime | None:
    """Wandelt gespeicherte Zeitstempel sicher in ``datetime`` um."""

    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_config() -> Dict[str, Any]:
    """Liest die gespeicherte Konfiguration ein."""

    with _LOCK:
        if not _CONFIG_PATH.exists():
            return dict(_DEFAULT_CONFIG)
        try:
            raw_text = _CONFIG_PATH.read_text(encoding="utf-8")
        except OSError:
            return dict(_DEFAULT_CONFIG)
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        _save_config(dict(_DEFAULT_CONFIG))
        return dict(_DEFAULT_CONFIG)
    if not isinstance(data, dict):
        _save_config(dict(_DEFAULT_CONFIG))
        return dict(_DEFAULT_CONFIG)
    enabled = bool(data.get("enabled", False))
    activated_at = data.get("activated_at")
    return {"enabled": enabled, "activated_at": activated_at}


def _save_config(data: Dict[str, Any]) -> None:
    """Speichert die Konfiguration. Bei Fehlern kann Debugging aktiviert werden."""

    serializable = {
        "enabled": bool(data.get("enabled", False)),
        "activated_at": _format_timestamp(_parse_timestamp(data.get("activated_at"))),
    }
    with _LOCK:
        try:
            _CONFIG_PATH.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            # Für detailliertes Debugging kann hier ``st.write`` aktiviert werden.
            pass


def _update_session(active: bool) -> None:
    """Synchronisiert den Session-State mit dem aktuellen Status."""

    st.session_state[SESSION_STATE_KEY] = active


def get_chatgpt_amboss_state() -> Tuple[bool, datetime | None]:
    """Liefert den gespeicherten Status und den Aktivierungszeitpunkt."""

    config = _load_config()
    enabled = bool(config.get("enabled", False))
    activated_at = _parse_timestamp(config.get("activated_at"))
    return enabled, activated_at


def is_chatgpt_amboss_active(now: datetime | None = None) -> bool:
    """Prüft, ob die Aktivierung noch gültig ist."""

    current_time = now or datetime.now(timezone.utc)
    enabled, activated_at = get_chatgpt_amboss_state()

    if not enabled:
        _update_session(False)
        return False

    if activated_at is None:
        activate_chatgpt_amboss(now=current_time)
        _update_session(True)
        return True

    if activated_at + PERSISTENCE_DURATION < current_time:
        deactivate_chatgpt_amboss()
        _update_session(False)
        return False

    _update_session(True)
    return True


def sync_chatgpt_amboss_session_state(now: datetime | None = None) -> bool:
    """Aktualisiert den Session-State und gibt den Status zurück."""

    active = is_chatgpt_amboss_active(now=now)
    _update_session(active)
    return active


def activate_chatgpt_amboss(*, now: datetime | None = None) -> None:
    """Aktiviert die Funktion und speichert den Zeitpunkt dauerhaft."""

    moment = now or datetime.now(timezone.utc)
    _save_config({"enabled": True, "activated_at": moment.isoformat(timespec="seconds")})
    _update_session(True)


def deactivate_chatgpt_amboss() -> None:
    """Deaktiviert die Funktion und setzt alle Marker zurück."""

    _save_config(dict(_DEFAULT_CONFIG))
    _update_session(False)
    st.session_state.pop("amboss_result", None)
    st.session_state.pop("amboss_input_mcp", None)

