"""Zentrale Lesezugriffe auf Supabase für Verhaltensoptionen und Hinweis-Texte."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import streamlit as st
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Konstanten für die gemeinsam genutzte Supabase-Tabelle.
# ---------------------------------------------------------------------------

# Name der Supabase-Tabelle, in der sowohl die Verhaltensoptionen als auch
# besondere Hinweis-Texte (z. B. der Begrüßungssatz) gespeichert werden.
# Die Tabelle wird im README näher beschrieben, einschließlich des SQL-Skripts
# zur Erstellung in Supabase.
_CONTENT_TABLE = "kommunikationshinweise"

# Werte für die Spalte ``category`` der Tabelle. Über sie wird gesteuert,
# ob ein Datensatz ein Verhalten ("behavior_option") oder ein Hinweistext
# ("special_hint") darstellt.
_CATEGORY_BEHAVIOR = "behavior_option"
_CATEGORY_HINT = "special_hint"


class SupabaseContentError(RuntimeError):
    """Sammel-Exception für Lesefehler in der Kommunikationshinweis-Tabelle."""


@dataclass(frozen=True)
class _ContentEntry:
    """Hilfsstruktur für Zeilen aus der Supabase-Tabelle."""

    slug: str
    content: str
    label: str | None = None


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


def _parse_entry(row: Dict[str, Any]) -> _ContentEntry | None:
    """Konvertiert eine geladene Tabellenzeile in eine geprüfte Struktur."""

    slug = str(row.get("slug", "")).strip()
    if not slug:
        return None

    content = str(row.get("content", "")).strip()
    if not content:
        return None

    label_value = row.get("label")
    label = str(label_value).strip() if isinstance(label_value, str) else None
    return _ContentEntry(slug=slug, content=content, label=label)


@st.cache_data(show_spinner=False)
def _load_entries_for_category(category: str) -> dict[str, _ContentEntry]:
    """Liest alle aktiven Einträge einer Kategorie aus Supabase."""

    client = _get_supabase_client()
    try:
        response = (
            client.table(_CONTENT_TABLE)
            .select("slug,label,content,is_active")
            .eq("category", category)
            .eq("is_active", True)
            .order("slug", desc=False)
            .execute()
        )
    except Exception as exc:  # pragma: no cover - Netzwerkaussetzer schwer simulierbar
        raise SupabaseContentError(
            "Abruf der Tabelle 'kommunikationshinweise' ist fehlgeschlagen."
        ) from exc

    if getattr(response, "error", None):
        raise SupabaseContentError(
            f"Supabase meldet einen Fehler: {response.error}"
        )

    rows = response.data or []
    result: dict[str, _ContentEntry] = {}
    for row in rows:
        parsed = _parse_entry(dict(row))
        if not parsed:
            continue
        result[parsed.slug] = parsed

    return result


def clear_cached_content() -> None:
    """Invalidiert alle Cache-Einträge dieses Moduls."""

    _load_entries_for_category.clear()


def get_behavior_options() -> dict[str, str]:
    """Liefert sämtliche Verhaltensoptionen aus Supabase."""

    eintraege = _load_entries_for_category(_CATEGORY_BEHAVIOR)
    if not eintraege:
        raise SupabaseContentError(
            "Keine Verhaltensoptionen in Supabase gefunden. Bitte Tabelle prüfen."
        )

    # Wir geben ein einfaches Dict zurück, damit bestehende Aufrufer weiterhin
    # ein Mapping von Schlüssel zu Beschreibung erhalten.
    return {slug: entry.content for slug, entry in eintraege.items()}


def get_special_hint(slug: str) -> str:
    """Gibt einen benannten Hinweistext (z. B. den Begrüßungssatz) zurück."""

    slug_clean = str(slug).strip().lower()
    if not slug_clean:
        raise SupabaseContentError(
            "Hinweis konnte nicht geladen werden: Ungültiger oder leerer Schlüssel."
        )

    hinweise = _load_entries_for_category(_CATEGORY_HINT)
    if not hinweise:
        raise SupabaseContentError(
            "Keine Hinweis-Texte in Supabase gefunden. Bitte Tabelle prüfen."
        )

    eintrag = hinweise.get(slug_clean)
    if not eintrag:
        raise SupabaseContentError(
            f"Hinweis '{slug_clean}' ist nicht in Supabase hinterlegt."
        )

    return eintrag.content
