"""Zentrale Lesezugriffe auf Supabase für Patient*innenverhalten."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import streamlit as st
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Konstanten für die gemeinsam genutzte Supabase-Tabelle.
# ---------------------------------------------------------------------------

# Name der Supabase-Tabelle, in der jede Zeile eine Verhaltenskonfiguration
# beschreibt (Prompt + Begrüßungssatz). Die genaue Tabellenstruktur inklusive
# SQL-Befehl ist im README erläutert.
_BEHAVIOR_TABLE = "patientenverhalten"


class SupabaseContentError(RuntimeError):
    """Sammel-Exception für Lesefehler in der Verhaltenstabelle."""


@dataclass(frozen=True)
class BehaviorEntry:
    """Abbild einer Tabellenzeile mit Prompt und Begrüßung."""

    key: str
    title: str
    prompt: str
    greeting: str


def _get_supabase_client() -> Client:
    """Erstellt einen Supabase-Client anhand der Streamlit-Secrets."""

    supabase_config = st.secrets.get("supabase")
    if not supabase_config:
        raise SupabaseContentError(
            "Supabase-Konfiguration fehlt in st.secrets. Bitte Abschnitt 'supabase' ergänzen."
        )

    try:
        url = supabase_config["url"]
        key = supabase_config["key"]
    except KeyError as exc:  # pragma: no cover - defensive Absicherung
        raise SupabaseContentError(
            "Supabase-Zugangsdaten sind unvollständig. Erwartet werden 'url' und 'key'."
        ) from exc

    try:
        return create_client(url, key)
    except Exception as exc:  # pragma: no cover - Netzwerkfehler schwer testbar
        raise SupabaseContentError(
            "Verbindung zu Supabase fehlgeschlagen. Siehe Debug-Hinweise in den Kommentaren."
        ) from exc


def _parse_behavior_row(row: Dict[str, Any]) -> BehaviorEntry | None:
    """Konvertiert eine geladene Tabellenzeile in eine geprüfte Struktur."""

    raw_title = str(row.get("verhalten_titel", "")).strip()
    if not raw_title:
        return None

    prompt = str(row.get("verhalten_prompt", "")).strip()
    if not prompt:
        return None

    greeting = str(row.get("verhalten_begrussung", "")).strip()
    if not greeting:
        return None

    key = raw_title.lower()
    return BehaviorEntry(key=key, title=raw_title, prompt=prompt, greeting=greeting)


@st.cache_data(show_spinner=False)
def _load_behavior_entries() -> dict[str, BehaviorEntry]:
    """Liest alle aktiven Verhaltensoptionen aus Supabase."""

    client = _get_supabase_client()
    try:
        response = (
            client.table(_BEHAVIOR_TABLE)
            .select("verhalten_titel,verhalten_prompt,verhalten_begrussung,is_active")
            .eq("is_active", True)
            .order("verhalten_titel", desc=False)
            .execute()
        )
    except Exception as exc:  # pragma: no cover - Netzwerkaussetzer schwer simulierbar
        raise SupabaseContentError(
            "Abruf der Tabelle 'patientenverhalten' ist fehlgeschlagen."
        ) from exc

    if getattr(response, "error", None):
        raise SupabaseContentError(
            f"Supabase meldet einen Fehler: {response.error}"
        )

    rows = response.data or []
    # Debugging-Hinweis: Bei Bedarf kann hier ein ``st.write(rows)`` aktiviert werden,
    # um die rohen Supabase-Daten temporär einzublenden. Das erleichtert das Auffinden
    # von Tippfehlern in Spaltennamen oder deaktivierten Datensätzen.
    result: dict[str, BehaviorEntry] = {}
    for row in rows:
        parsed = _parse_behavior_row(dict(row))
        if not parsed:
            continue
        result[parsed.key] = parsed

    return result


def clear_cached_content() -> None:
    """Invalidiert alle Cache-Einträge dieses Moduls."""

    _load_behavior_entries.clear()


def get_behavior_options() -> dict[str, BehaviorEntry]:
    """Liefert sämtliche Verhaltensoptionen aus Supabase."""

    eintraege = _load_behavior_entries()
    if not eintraege:
        raise SupabaseContentError(
            "Keine Verhaltensoptionen in Supabase gefunden. Bitte Tabelle prüfen."
        )

    return eintraege


def get_behavior_entry(key: str) -> BehaviorEntry:
    """Gibt eine konkrete Verhaltenszeile anhand des Titels zurück."""

    key_clean = str(key).strip().lower()
    if not key_clean:
        raise SupabaseContentError(
            "Verhalten konnte nicht geladen werden: Ungültiger oder leerer Schlüssel."
        )

    eintraege = _load_behavior_entries()
    if not eintraege:
        raise SupabaseContentError(
            "Keine Verhaltensoptionen in Supabase gefunden. Bitte Tabelle prüfen."
        )

    eintrag = eintraege.get(key_clean)
    if not eintrag:
        raise SupabaseContentError(
            f"Verhalten '{key_clean}' ist nicht in Supabase hinterlegt."
        )

    return eintrag
