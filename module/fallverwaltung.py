"""Hilfsfunktionen zur Verwaltung und Auswahl der Fallszenarien."""
from __future__ import annotations

import random
from io import BytesIO
from typing import Iterable

import pandas as pd
import streamlit as st

try:  # pragma: no cover - optional dependency safeguard
    import requests
except Exception:  # pragma: no cover - fallback when requests is unavailable
    requests = None  # type: ignore[assignment]


DEFAULT_FALLDATEI = "fallbeispiele.xlsx"
DEFAULT_FALLDATEI_URL = (
    "https://github.com/WALLJE/Karina-Chat/raw/main/fallbeispiele.xlsx"
)

_FALL_SESSION_KEYS: set[str] = {
    "diagnose_szenario",
    "diagnose_features",
    "koerper_befund_tip",
    "patient_alter_basis",
    "patient_gender",
    "patient_name",
    "patient_age",
    "patient_job",
    "patient_verhalten_memo",
    "patient_verhalten",
    "patient_hauptanweisung",
    "SYSTEM_PROMPT",
    "startzeit",
    "start_untersuchung",
    "untersuchung_done",
    "diagnostik_aktiv",
    "diagnostik_runden_gesamt",
    "messages",
    "koerper_befund",
    "user_ddx2",
    "user_diagnostics",
    "befunde",
    "diagnostik_eingaben",
    "gpt_befunde",
    "diagnostik_eingaben_kumuliert",
    "gpt_befunde_kumuliert",
    "final_diagnose",
    "therapie_vorschlag",
    "final_feedback",
    "feedback_prompt_final",
    "feedback_row_id",
    "student_evaluation_done",
    "token_sums",
}

_FALL_SESSION_PREFIXES: tuple[str, ...] = (
    "diagnostik_runde_",
    "befunde_runde_",
)


def lade_fallbeispiele(*, url: str | None = None, pfad: str | None = None) -> pd.DataFrame:
    """Liest die Fallbeispiele als DataFrame ein.

    Args:
        url: Optionale URL, von der die Datei geladen werden soll.
        pfad: Optionaler Pfad zu einer lokalen Excel-Datei.

    Returns:
        Ein DataFrame mit den Fallszenarien oder ein leerer DataFrame bei Fehlern.
    """

    if url:
        if requests is None:
            st.error("❌ Die Bibliothek 'requests' ist nicht verfügbar.")
            return pd.DataFrame()
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - reine IO-Fehlerbehandlung
            st.error(f"❌ Fehler beim Laden der Fallszenarien: {exc}")
            return pd.DataFrame()
        try:
            return pd.read_excel(BytesIO(response.content))
        except Exception as exc:  # pragma: no cover - Pandas-Fehler
            st.error(f"❌ Die Fallliste konnte nicht eingelesen werden: {exc}")
            return pd.DataFrame()

    pfad = pfad or DEFAULT_FALLDATEI
    try:
        return pd.read_excel(pfad)
    except FileNotFoundError:
        st.error(f"❌ Die Datei '{pfad}' wurde nicht gefunden.")
    except Exception as exc:  # pragma: no cover - Pandas-Fehler
        st.error(f"❌ Die Fallliste konnte nicht eingelesen werden: {exc}")
    return pd.DataFrame()


def fallauswahl_prompt(df: pd.DataFrame, szenario: str | None = None) -> None:
    """Übernimmt ein zufälliges oder vorgegebenes Szenario in den Session State."""

    if df.empty:
        st.error("📄 Die Falltabelle ist leer oder konnte nicht geladen werden.")
        return

    try:
        fall = _waehle_fall(df, szenario)
    except (IndexError, KeyError, ValueError) as exc:
        st.error(f"❌ Fehler beim Auswählen des Falls: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive fallback
        st.error(f"❌ Unerwarteter Fehler beim Laden des Falls: {exc}")
        return

    st.session_state.diagnose_szenario = fall.get("Szenario", "")
    st.session_state.diagnose_features = fall.get("Beschreibung", "")
    st.session_state.koerper_befund_tip = fall.get("Körperliche Untersuchung", "")

    alter_roh = fall.get("Alter")
    try:
        alter_berechnet = int(float(alter_roh)) if alter_roh not in (None, "") else None
    except (TypeError, ValueError):
        alter_berechnet = None
    st.session_state.patient_alter_basis = alter_berechnet

    geschlecht = str(fall.get("Geschlecht", "")).strip().lower()
    if geschlecht == "n":
        geschlecht = random.choice(["m", "w"])
    elif geschlecht not in {"m", "w"}:
        geschlecht = ""
    st.session_state.patient_gender = geschlecht


def reset_fall_session_state(keep_keys: Iterable[str] | None = None) -> None:
    """Entfernt alle fallbezogenen Werte aus dem Session State."""

    keys_to_keep = set(keep_keys or [])
    for key in list(st.session_state.keys()):
        if key in keys_to_keep:
            continue
        if key in _FALL_SESSION_KEYS or any(key.startswith(prefix) for prefix in _FALL_SESSION_PREFIXES):
            st.session_state.pop(key, None)


def _waehle_fall(df: pd.DataFrame, szenario: str | None) -> pd.Series:
    """Hilfsfunktion, um ein Szenario aus dem DataFrame zu selektieren."""

    if szenario:
        gefundene = df[df["Szenario"] == szenario]
        if gefundene.empty:
            raise ValueError(f"Szenario '{szenario}' nicht in der Tabelle gefunden.")
        return gefundene.iloc[0]
    return df.sample(1).iloc[0]


__all__ = [
    "DEFAULT_FALLDATEI",
    "DEFAULT_FALLDATEI_URL",
    "fallauswahl_prompt",
    "lade_fallbeispiele",
    "reset_fall_session_state",
]
