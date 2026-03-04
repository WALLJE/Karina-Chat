"""On-Demand-Vertiefung für das Abschlussfeedback (Variante 2).

Dieses Modul ergänzt die kompakte Feedback-Ausgabe um optionale, ausklappbare
Lehrbuch-Details pro Unterpunkt. Die Details werden nur bei Klick generiert,
um Token zu sparen. Zusätzlich werden Nutzung und Text in Supabase protokolliert
(Option A: Ereignis-Tabelle) und gecachte Detailtexte nach 3 Monaten erneuert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re
from typing import Dict, List, Tuple

import streamlit as st
from supabase import Client, create_client

from module.offline import is_offline

# Modellentscheidung für die Detailtexte:
# - gpt-4.1-mini ist im Vergleich zu größeren Modellen meist schneller,
#   günstiger und für strukturierte, nicht-personalisierte Lehrbuchtexte
#   in der Regel ausreichend präzise.
# - Das Abschlussfeedback selbst bleibt weiterhin im Hauptmodul auf gpt-4.1.
DETAIL_MODEL = "gpt-4.1-mini"

# Ein Cache-Eintrag gilt 90 Tage (~3 Monate) als frisch.
CACHE_TTL_DAYS = 90

# Erwartete Unterpunkte von Variante 2.
SECTION_TITLES: Dict[str, str] = {
    "anamnese": "Anamnese",
    "diagnostik_szenario": "Diagnostik – Szenario",
    "diagnostik_ddx": "Diagnostik – Differentialdiagnosen",
    "strategie": "Diagnostische Strategie",
    "finale_diagnose": "Finale Diagnose",
    "therapie_setting": "Therapiekonzept & Setting",
}

# Regex für nummerierte Unterpunkte wie "1. **Anamnese:**".
_SECTION_PATTERN = re.compile(
    r"(?ms)^\s*(?P<number>[1-6])\.\s*\*\*(?P<title>[^*]+)\*\*:?\s*(?P<body>.*?)(?=^\s*[1-6]\.\s*\*\*|\Z)"
)


@dataclass
class FeedbackSection:
    """Repräsentiert einen erkannten nummerierten Feedback-Unterpunkt."""

    number: int
    title: str
    body: str
    key: str


def _get_supabase_client() -> Client:
    """Erzeugt einen Supabase-Client aus ``st.secrets``.

    Debug-Hinweis:
    Bei Verbindungsproblemen kann temporär `st.write(st.secrets.get("supabase"))`
    aktiviert werden, um zu prüfen, ob URL/Key korrekt geladen wurden.
    """

    cfg = st.secrets.get("supabase")
    if not cfg:
        raise RuntimeError("Supabase-Konfiguration fehlt in st.secrets['supabase'].")
    return create_client(cfg["url"], cfg["key"])


def _normalize_title_to_key(title: str, number: int) -> str:
    """Leitet einen stabilen Schlüssel je Unterpunkt aus Titel/Nummer ab."""

    t = title.lower()
    if "anamnese" in t:
        return "anamnese"
    if "differential" in t:
        return "diagnostik_ddx"
    if "strategie" in t:
        return "strategie"
    if "final" in t and "diagnose" in t:
        return "finale_diagnose"
    if "therapie" in t or "setting" in t:
        return "therapie_setting"
    if "diagnostik" in t:
        return "diagnostik_szenario"

    # Fallback auf Nummer, damit bei leicht geänderten Titeln trotzdem
    # ein stabiler Key erzeugt wird.
    num_map = {
        1: "anamnese",
        2: "diagnostik_szenario",
        3: "diagnostik_ddx",
        4: "strategie",
        5: "finale_diagnose",
        6: "therapie_setting",
    }
    return num_map.get(number, f"section_{number}")


def split_feedback_sections(feedback_text: str) -> Tuple[str, List[FeedbackSection]]:
    """Teilt das Feedback in Einleitung und nummerierte Unterpunkte.

    Returns:
        (prefix_markdown, sections)
    """

    matches = list(_SECTION_PATTERN.finditer(feedback_text or ""))
    if not matches:
        return feedback_text, []

    first_start = matches[0].start()
    prefix = feedback_text[:first_start].strip()
    sections: List[FeedbackSection] = []

    for match in matches:
        number = int(match.group("number"))
        title = (match.group("title") or "").strip()
        body = (match.group("body") or "").strip()
        key = _normalize_title_to_key(title, number)
        sections.append(FeedbackSection(number=number, title=title, body=body, key=key))

    return prefix, sections


def _make_cache_key(section_key: str, section_body: str) -> str:
    """Baut einen stabilen Cache-Key aus Unterpunkt und Basisinhalt."""

    digest = hashlib.sha256(f"{section_key}|{section_body.strip()}|v1".encode("utf-8")).hexdigest()
    return digest


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _cache_is_fresh(updated_at: str | None) -> bool:
    """Prüft, ob der Cache jünger als 90 Tage ist."""

    parsed = _parse_iso_datetime(updated_at)
    if not parsed:
        return False
    return (datetime.now(timezone.utc) - parsed) <= timedelta(days=CACHE_TTL_DAYS)


def _generate_detail_text(section: FeedbackSection) -> str:
    """Generiert einen nicht-personalisierten Lehrbuchtext für einen Unterpunkt."""

    if is_offline():
        raise RuntimeError("Detailtext-Generierung ist im Offline-Modus nicht verfügbar.")

    client = st.session_state.get("openai_client")
    if client is None:
        raise RuntimeError("OpenAI-Client fehlt im Session-State (openai_client).")

    prompt = f"""
Erstelle einen sachlichen, nicht-personalisierten Lehrbuchtext auf Deutsch (ca. 150 Wörter).
Thema des Unterpunkts: {section.title}
Kernaussage aus dem kompakten Feedback:
{section.body}

Anforderungen:
- Kein direktes Ansprechen (kein "du", keine Personalpronomen für Lernende).
- Struktur in drei Mini-Abschnitten mit Zwischenüberschriften:
  1) Klinische Relevanz
  2) Leitliniengerechtes Vorgehen
  3) Häufige Fehler und Abgrenzung
- Neutraler, präziser Lehrbuchstil.
- Keine erfundenen Quellenangaben oder Leitliniennummern.
- Inhalt allgemein halten (nicht auf einzelne Person beziehen).
""".strip()

    response = client.chat.completions.create(
        model=DETAIL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def _load_cached_detail(supabase: Client, cache_key: str) -> Tuple[str | None, bool]:
    """Lädt vorhandenen Cache-Eintrag und markiert, ob er noch frisch ist."""

    response = (
        supabase.table("feedback_detail_cache")
        .select("detail_text, updated_at")
        .eq("cache_key", cache_key)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None, False

    row = rows[0]
    return row.get("detail_text"), _cache_is_fresh(row.get("updated_at"))


def _save_cache_detail(supabase: Client, cache_key: str, section_key: str, detail_text: str) -> None:
    """Schreibt/aktualisiert den generierten Detailtext in den Cache."""

    supabase.table("feedback_detail_cache").upsert(
        {
            "cache_key": cache_key,
            "section_key": section_key,
            "detail_text": detail_text,
            "model": DETAIL_MODEL,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="cache_key",
    ).execute()


def _sync_default_events(supabase: Client, feedback_id: int, sections: List[FeedbackSection]) -> None:
    """Legt pro Unterpunkt einen Default-Event mit `opened=false` an.

    Damit wird in Supabase explizit sichtbar, dass ein Feld vorhanden war, aber
    nicht geöffnet wurde ("Nein"). Bei späterem Öffnen wird derselbe Datensatz
    auf `opened=true` aktualisiert.
    """

    # WICHTIG:
    # Diese Funktion darf bei Streamlit-Reruns bereits geöffnete Punkte NICHT
    # zurücksetzen. Daher werden nur fehlende Einträge neu angelegt.
    defaults = [
        {
            "feedback_id": feedback_id,
            "section_key": section.key,
            "section_title": section.title,
            "opened": False,
            "generated_text": "Nein",
        }
        for section in sections
    ]
    if not defaults:
        return

    # Bereits vorhandene section_keys für dieses Feedback ermitteln.
    # So verhindern wir, dass bestehende opened/generated_text-Werte bei jedem
    # Rerun überschrieben werden.
    existing_response = (
        supabase.table("feedback_detail_events")
        .select("section_key")
        .eq("feedback_id", feedback_id)
        .execute()
    )
    existing_rows = existing_response.data or []
    existing_keys = {row.get("section_key") for row in existing_rows if row.get("section_key")}

    missing_defaults = [row for row in defaults if row["section_key"] not in existing_keys]
    if not missing_defaults:
        return

    # Nur fehlende Default-Zeilen einfügen (kein Upsert), damit vorhandene
    # Nutzungsdaten stabil bleiben.
    supabase.table("feedback_detail_events").insert(missing_defaults).execute()


def _save_open_event(
    supabase: Client,
    feedback_id: int,
    section: FeedbackSection,
    detail_text: str,
) -> None:
    """Aktualisiert den Event-Eintrag auf `opened=true` und speichert den Text."""

    supabase.table("feedback_detail_events").upsert(
        {
            "feedback_id": feedback_id,
            "section_key": section.key,
            "section_title": section.title,
            "opened": True,
            "generated_text": detail_text,
            "model": DETAIL_MODEL,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="feedback_id,section_key",
    ).execute()


def render_feedback_with_details(feedback_text: str) -> None:
    """Rendert das kompakte Feedback + On-Demand-Aufklapper je Unterpunkt.

    Wichtiger Ablauf:
    1) Kompaktes Feedback anzeigen (Variante-2-Stil bleibt erhalten).
    2) Je Unterpunkt ein Expander mit explizitem Lade-Button.
    3) Erst bei Klick KI-Text laden/generieren + in Supabase protokollieren.
    """

    prefix, sections = split_feedback_sections(feedback_text)
    if not sections:
        st.markdown(feedback_text)
        return

    feedback_id = st.session_state.get("feedback_row_id")
    supabase = None
    if not is_offline() and feedback_id:
        try:
            supabase = _get_supabase_client()
            _sync_default_events(supabase, int(feedback_id), sections)
        except Exception as exc:
            st.warning(f"⚠️ Supabase-Sync für Detail-Events fehlgeschlagen: {exc}")

    if prefix:
        st.markdown(prefix)

    st.caption(
        "💡 Kompakte Bewertung zuerst; zusätzliche Lehrbuch-Details können pro Unterpunkt bei Bedarf geladen werden."
    )

    detail_cache_state = st.session_state.setdefault("feedback_detail_runtime_cache", {})

    for section in sections:
        st.markdown(f"{section.number}. **{section.title}:**  {section.body}")

        expander_label = f"Mehr Infos zu Punkt {section.number} ({SECTION_TITLES.get(section.key, section.title)})"
        with st.expander(expander_label, expanded=False):
            button_key = f"load_detail_{section.number}_{section.key}"
            if st.button("Lehrbuch-Vertiefung laden", key=button_key):
                cache_key = _make_cache_key(section.key, section.body)

                # 1) Laufzeit-Cache in Streamlit-Session prüfen (schnellster Pfad).
                detail_text = detail_cache_state.get(cache_key)

                # 2) Persistenten Supabase-Cache prüfen.
                from_supabase_cache = False
                if detail_text is None and supabase is not None:
                    try:
                        cached_text, is_fresh = _load_cached_detail(supabase, cache_key)
                        if cached_text and is_fresh:
                            detail_text = cached_text
                            from_supabase_cache = True
                    except Exception as exc:
                        st.warning(f"⚠️ Lesen des Detail-Caches fehlgeschlagen: {exc}")

                # 3) Falls kein frischer Cache vorliegt: neu generieren.
                if detail_text is None:
                    try:
                        with st.spinner("⏳ KI erstellt die Vertiefung..."):
                            detail_text = _generate_detail_text(section)
                    except Exception as exc:
                        # Debug-Hinweis:
                        # Wenn diese Meldung häufiger auftritt, temporär
                        # `st.write("offline:", is_offline())` und
                        # `st.write("openai_client vorhanden:", bool(st.session_state.get("openai_client")))`
                        # aktivieren, um den Zustand direkt im UI zu prüfen.
                        st.warning(f"⚠️ Vertiefung konnte nicht erzeugt werden: {exc}")
                        st.info("ℹ️ Bitte später erneut versuchen oder Offline-Modus prüfen.")
                        continue
                    if supabase is not None:
                        try:
                            _save_cache_detail(supabase, cache_key, section.key, detail_text)
                        except Exception as exc:
                            st.warning(f"⚠️ Schreiben des Detail-Caches fehlgeschlagen: {exc}")

                # Laufzeit-Cache immer aktualisieren.
                detail_cache_state[cache_key] = detail_text

                if from_supabase_cache:
                    st.caption("♻️ Aus Supabase-Cache geladen (jünger als 3 Monate).")

                st.markdown(detail_text)

                if supabase is not None and feedback_id:
                    try:
                        _save_open_event(supabase, int(feedback_id), section, detail_text)
                    except Exception as exc:
                        st.warning(f"⚠️ Speichern des Öffnungs-Events fehlgeschlagen: {exc}")

            # Bereits geladene Inhalte bei erneutem Öffnen erneut anzeigen.
            cache_key = _make_cache_key(section.key, section.body)
            already_loaded = detail_cache_state.get(cache_key)
            if already_loaded:
                st.markdown(already_loaded)
