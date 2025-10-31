"""Verwaltet die GPT-Zusammenfassung des AMBOSS-Payloads im Session State."""

from __future__ import annotations

from typing import Optional

import streamlit as st


SUMMARY_KEY = "amboss_summary"
"""Session-State-Schlüssel für den aktuell gespeicherten Zusammenfassungstext."""


def hole_amboss_zusammenfassung() -> Optional[str]:
    """Liest die zuletzt erzeugte Zusammenfassung aus dem Session State."""

    return st.session_state.get(SUMMARY_KEY)


def speichere_zusammenfassung(text: str) -> None:
    """Persistiert den angegebenen Text ohne weitere Metadaten."""

    st.session_state[SUMMARY_KEY] = text


def loesche_zusammenfassung() -> None:
    """Entfernt die aktuelle Zusammenfassung aus dem Session State."""

    st.session_state.pop(SUMMARY_KEY, None)


__all__ = [
    "hole_amboss_zusammenfassung",
    "speichere_zusammenfassung",
    "loesche_zusammenfassung",
    "SUMMARY_KEY",
]
