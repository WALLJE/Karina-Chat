"""On-Demand-Vertiefung für das Abschlussfeedback (Variante 2).

Dieses Modul ergänzt die kompakte Feedback-Ausgabe um optionale, ausklappbare
Details pro Unterpunkt. Die Details werden nur bei Klick generiert,
um Token zu sparen. Zusätzlich werden Nutzung und Text in Supabase protokolliert
(Option A: Ereignis-Tabelle) und gecachte Detailtexte nach 3 Monaten erneuert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Tuple

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
    "therapie_setting": "Therapiekonzept und Setting",
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


def _make_cache_key(
    section_key: str,
    section_body: str,
    feedback_id: int | None,
    fall_id: str | int | None = None,
    feedback_mode: str | None = None,
    section_context: Dict[str, Any] | None = None,
) -> str:
    """Baut einen stabilen Cache-Key mit fachlichem Kontext für den Unterpunkt.

    Warum diese Erweiterung wichtig ist:
    Früher war der Cache faktisch global pro Unterpunkttext. Das konnte dazu
    führen, dass in einem anderen Fall ein fachlich ähnlicher Abschnitt einen
    alten Text wiederverwendet hat, obwohl der neue Fallkontext abweicht.
    Mindestens die ``feedback_id`` muss deshalb in den Hash einfließen.
    Optional werden auch ``fall_id`` und ``feedback_mode`` ergänzt.

    Seit der kontextsensitiven Detailgenerierung reicht das allein aber nicht:
    Der gleiche Unterpunkttext kann je nach ``section_context`` unterschiedliche
    Vertiefungen erzeugen. Deshalb fließt ein stabil serialisierter Kontext
    ebenfalls in den Hash ein.

    Debug-Hilfe (bei unerwarteten Cache-Treffern):
    Temporär kann `st.write("cache_key_input", {...})` vor dem Hash aktiviert
    werden, um die verwendeten Eingaben sichtbar zu machen.
    """

    # Wichtig für deterministische Keys: JSON mit sortierten Schlüsseln und
    # expliziter Trennung. So bleibt der Hash bei identischem Kontext stabil,
    # auch wenn Python-Dicts intern anders angeordnet wurden.
    context_payload = json.dumps(section_context or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    key_input = (
        f"section={section_key}|"
        f"body={section_body.strip()}|"
        f"feedback_id={feedback_id}|"
        f"fall_id={fall_id}|"
        f"feedback_mode={feedback_mode}|"
        f"context={context_payload}|"
        "v2"
    )
    digest = hashlib.sha256(key_input.encode("utf-8")).hexdigest()
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


def _build_section_context(section: FeedbackSection) -> Dict[str, Any]:
    """Stellt je Unterpunkt gezielt den erlaubten Prompt-Kontext zusammen.

    Wichtige Designentscheidung:
    Für die Vertiefungstexte darf nicht der gesamte Session-State verwendet
    werden, da dies die Antwort unnötig aufbläht und Inhalte in Abschnitte
    leaken kann, in denen sie didaktisch nichts zu suchen haben.

    Die Funktion liefert deshalb bewusst einen *strukturierten* Kontext mit
    eng begrenzten Feldern pro ``section.key``. Diese Begrenzung ist kein
    technischer Zufall, sondern ein fachlicher Guardrail.
    """

    feedback_mode = str(st.session_state.get("feedback_mode", "")).strip() or "ChatGPT"
    context: Dict[str, Any] = {
        "feedback_mode": feedback_mode,
        "section_key": section.key,
    }

    # Zentrale Befundsammlung: Die Detailtexte für Diagnostik-Abschnitte sollen
    # gezielt mit realen Befunden arbeiten. Wir sammeln nur fachlich relevante
    # Befundquellen und geben sie strukturiert weiter.
    relevante_befunde: Dict[str, str] = {}
    if st.session_state.get("koerper_befund"):
        relevante_befunde["koerper_befund"] = str(st.session_state.get("koerper_befund", "")).strip()
    if st.session_state.get("befunde"):
        relevante_befunde["initiale_befunde"] = str(st.session_state.get("befunde", "")).strip()

    diagnostik_runden_gesamt = int(st.session_state.get("diagnostik_runden_gesamt", 1) or 1)
    for i in range(2, diagnostik_runden_gesamt + 1):
        befund_key = f"befunde_runde_{i}"
        if st.session_state.get(befund_key):
            relevante_befunde[befund_key] = str(st.session_state.get(befund_key, "")).strip()

    # Abschnitt 1: Anamnese bekommt bewusst nur den Gesprächsverlauf
    # (Anamneseteil) + optional Szenario-Kontext. Keine Diagnostikdetails,
    # damit die Vertiefung sauber auf Gesprächsführung fokussiert bleibt.
    if section.key == "anamnese":
        context["user_verlauf"] = str(st.session_state.get("user_verlauf", "")).strip()
        if st.session_state.get("diagnose_szenario"):
            context["diagnose_szenario"] = str(st.session_state.get("diagnose_szenario", "")).strip()

    # Abschnitt 2b: DDX-Teil bekommt nur DDX + kumulierte Diagnostik + Befunde.
    # Kein vollständiger Verlauf, damit Differentialdiagnosen nicht mit
    # Gesprächsrauschen vermischt werden.
    elif section.key == "diagnostik_ddx":
        context["user_ddx2"] = str(st.session_state.get("user_ddx2", "")).strip()
        context["diagnostik_eingaben_kumuliert"] = str(
            st.session_state.get("diagnostik_eingaben_kumuliert", "")
        ).strip()
        context["relevante_befunde"] = relevante_befunde

    # Abschnitt 2a: Diagnostik-Szenario kombiniert Diagnostikdaten, Szenario
    # und Befunde, aber *ohne* vollständigen Gesprächsverlauf.
    elif section.key == "diagnostik_szenario":
        context["diagnostik_eingaben_kumuliert"] = str(
            st.session_state.get("diagnostik_eingaben_kumuliert", "")
        ).strip()
        context["diagnose_szenario"] = str(st.session_state.get("diagnose_szenario", "")).strip()
        context["relevante_befunde"] = relevante_befunde

    # Abschnitte 5/6: Finale Diagnose/Therapie/Setting nur im Zielbild.
    # Frühere Hypothesen oder Verlauf werden absichtlich nicht ergänzt, damit
    # der Abschnitt auf Management-Entscheidungen fokussiert bleibt.
    elif section.key in {"finale_diagnose", "therapie_setting"}:
        context["final_diagnose"] = str(st.session_state.get("final_diagnose", "")).strip()
        context["therapie_vorschlag"] = str(st.session_state.get("therapie_vorschlag", "")).strip()
        context["therapie_setting_verdacht"] = str(
            st.session_state.get("therapie_setting_verdacht", "")
        ).strip()
        context["therapie_setting_final"] = str(st.session_state.get("therapie_setting_final", "")).strip()

    # Für alle anderen Abschnitte (z. B. "strategie") halten wir den Kontext
    # bewusst minimal. Debug-Hilfe bei Bedarf:
    # st.write("Detail-Kontext Strategie:", context)

    # Modusabhängige Kontextfreigabe:
    # - ChatGPT: kein AMBOSS-Zusatzkontext.
    # - Amboss_ChatGPT: komprimierte AMBOSS-Zusammenfassung ergänzen.
    if feedback_mode == "Amboss_ChatGPT":
        amboss_summary = str(st.session_state.get("amboss_payload_summary", "")).strip()
        amboss_input_fallback = str(st.session_state.get("Amboss_Input", "")).strip()
        if amboss_summary:
            context["amboss_kontext"] = amboss_summary
        elif amboss_input_fallback:
            context["amboss_kontext"] = amboss_input_fallback
        # Debug-Hilfe: Falls im AMBOSS-Modus kein Kontext erscheint, temporär
        # folgende Zeile aktivieren und prüfen, welche Quelle leer ist:
        # st.write("AMBOSS Debug", amboss_summary, amboss_input_fallback)

    return context


def _generate_detail_text(section: FeedbackSection, context: Dict[str, Any]) -> str:
    """Generiert einen nicht-personalisierten, praxisnahen Detailtext je Unterpunkt."""

    if is_offline():
        raise RuntimeError("Detailtext-Generierung ist im Offline-Modus nicht verfügbar.")

    client = st.session_state.get("openai_client")
    if client is None:
        raise RuntimeError("OpenAI-Client fehlt im Session-State (openai_client).")

    prompt = f"""
Erstelle eine praxisnahe, nicht-personalisierte Vertiefung auf Deutsch für einen Feedback-Unterpunkt.

Unterpunkt: {section.title}
Kernaussage aus dem kompakten Feedback:
{section.body}

Strukturierter Abschnittskontext (nur erlaubte Felder):
{context}

Verbindliche Ausgabe-Regeln:
- Kein direktes Ansprechen (kein "du", keine Personalpronomen für Lernende).
- Fokus auf konkrete, praxisnahe klinische Formulierungen statt Allgemeinplätzen.
- Gib zuerst 4–6 kurze Bulletpoints mit klaren Handlungsimpulsen aus.
- Nur Inhalte verwenden, die zum Unterpunkt und zum gelieferten Kontext passen.
- Keine Quellenangaben, keine Leitliniennummern, keine erfundenen Details.
- Umfang kompakt halten (ca. 120–170 Wörter).
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


def _save_cache_detail(
    supabase: Client,
    cache_key: str,
    section_key: str,
    detail_text: str,
    feedback_id: int | None,
    fall_id: str | int | None,
    feedback_mode: str | None,
) -> None:
    """Schreibt/aktualisiert den generierten Detailtext in den Cache."""

    supabase.table("feedback_detail_cache").upsert(
        {
            "cache_key": cache_key,
            "section_key": section_key,
            "feedback_id": feedback_id,
            "fall_id": None if fall_id is None else str(fall_id),
            "feedback_modus": feedback_mode,
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
    defaults = []
    for section in sections:
        # Meta-Informationen werden bereits beim Default-Insert gespeichert,
        # damit auch nie geöffnete Unterpunkte für Auswertungen vollständig
        # vorliegen (z. B. welcher Modus aktiv war oder ob AMBOSS-Kontext
        # grundsätzlich verfügbar war).
        section_context = _build_section_context(section)
        defaults.append(
            {
                "feedback_id": feedback_id,
                "section_key": section.key,
                "section_title": section.title,
                "opened": False,
                "generated_text": "Nein",
                "feedback_modus": _get_feedback_modus(),
                "amboss_mcp_genutzt": _is_amboss_mcp_genutzt(),
                "zusaetzliche_infos_abgerufen": _has_zusaetzliche_infos(),
                "zusaetzliche_infos_quellen": _build_zusaetzliche_infos_quellen(section_context),
                "context_snapshot": section_context,
            }
        )
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

    # Kontext wird explizit hier neu aufgebaut, damit der gespeicherte Snapshot
    # exakt den Zustand zum Zeitpunkt des Öffnens widerspiegelt. Falls Inhalte
    # zwischen Default-Anlage und Klick geändert wurden, bleibt das im Event
    # transparent nachvollziehbar.
    section_context = _build_section_context(section)

    supabase.table("feedback_detail_events").upsert(
        {
            "feedback_id": feedback_id,
            "section_key": section.key,
            "section_title": section.title,
            "opened": True,
            "generated_text": detail_text,
            "model": DETAIL_MODEL,
            "feedback_modus": _get_feedback_modus(),
            "amboss_mcp_genutzt": _is_amboss_mcp_genutzt(),
            "zusaetzliche_infos_abgerufen": _has_zusaetzliche_infos(),
            "zusaetzliche_infos_quellen": _build_zusaetzliche_infos_quellen(section_context),
            "context_snapshot": section_context,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="feedback_id,section_key",
    ).execute()


def _get_feedback_modus() -> str:
    """Liest den aktuell aktiven Feedback-Modus robust aus dem Session-State."""

    return str(st.session_state.get("feedback_mode", "")).strip() or "ChatGPT"


def _is_amboss_mcp_genutzt() -> bool:
    """Kennzeichnet, ob die AMBOSS-Zusammenfassung aus MCP stammt."""

    return str(st.session_state.get("amboss_summary_source", "")).strip().lower() == "mcp"


def _has_zusaetzliche_infos() -> bool:
    """Leitet ab, ob zusätzliche Fachinfos für das Feedback verfügbar waren."""

    # Für die Auswertung genügt ein klarer Boolean:
    # - True, sobald irgendeine Zusatzquelle signalisiert wurde.
    # - False, wenn ausschließlich ChatGPT ohne Zusatzdaten lief.
    amboss_summary_source = str(st.session_state.get("amboss_summary_source", "")).strip()
    return bool(amboss_summary_source)


def _build_zusaetzliche_infos_quellen(section_context: Dict[str, Any]) -> Dict[str, Any]:
    """Baut strukturierte Metadaten für die Quelle der Zusatzinformationen."""

    amboss_summary_source = str(st.session_state.get("amboss_summary_source", "")).strip() or None
    verwendete_session_keys = sorted(
        [
            key
            for key in section_context.keys()
            if key
            not in {
                # Diese beiden Felder sind Steuerinfos des Moduls und keine
                # inhaltlichen Nutzdaten.
                "feedback_mode",
                "section_key",
            }
        ]
    )
    return {
        "amboss_summary_source": amboss_summary_source,
        "amboss_payload_summary_verfuegbar": bool(str(st.session_state.get("amboss_payload_summary", "")).strip()),
        "amboss_input_verfuegbar": bool(str(st.session_state.get("Amboss_Input", "")).strip()),
        "verwendete_context_keys": verwendete_session_keys,
    }


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
        "💡 Kompakte Bewertung zuerst; zusätzliche Details können pro Unterpunkt bei Bedarf geladen werden."
    )

    detail_cache_state = st.session_state.setdefault("feedback_detail_runtime_cache", {})

    for section in sections:
        st.markdown(f"**{section.number}. {section.title}**")
        st.markdown(section.body)

        # UI-Änderung gemäß Nutzerwunsch:
        # Statt Expander + klickbarer Fläche verwenden wir eine reine Dropdown-Interaktion.
        # Sobald der Unterpunkt im Dropdown ausgewählt ist, wird der Inhalt geladen und
        # unterhalb angezeigt. Für die Ladephase bleibt ein sichtbarer Spinner erhalten.
        option_label = f"Punkt {section.number}: {SECTION_TITLES.get(section.key, section.title)}"
        selector_key = f"detail_selector_{section.number}_{section.key}"
        # Wir merken uns die *vorherige* Auswahl explizit in einem separaten Session-Key.
        # Hintergrund: Bei Streamlit bleibt der Selectbox-Wert über Reruns erhalten.
        # Ohne Flankenerkennung würde das Öffnungs-Event bei jeder späteren Interaktion
        # erneut geschrieben und den ursprünglichen opened_at-Zeitpunkt überschreiben.
        previous_selection_key = f"{selector_key}_previous"
        previous_selection = st.session_state.get(previous_selection_key, "Keine Details laden")
        selected = st.selectbox(
            "Details auswählen",
            options=["Keine Details laden", option_label],
            key=selector_key,
            label_visibility="collapsed",
        )
        # Flankenerkennung: Nur wenn der Wert *neu* auf den Detailpunkt gewechselt ist,
        # gilt das als echtes Öffnen im aktuellen Run und darf als Event gespeichert werden.
        selection_just_activated = selected == option_label and previous_selection != option_label

        detail_rendered_in_this_run = False
        fall_id = st.session_state.get("fall_id")
        feedback_mode = str(st.session_state.get("feedback_mode", "")).strip() or None
        section_context = _build_section_context(section)
        cache_key = _make_cache_key(
            section.key,
            section.body,
            int(feedback_id) if feedback_id is not None else None,
            fall_id=fall_id,
            feedback_mode=feedback_mode,
            section_context=section_context,
        )

        if selected == option_label:
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
                    with st.spinner("⏳ KI lädt zusätzliche Details..."):
                        detail_text = _generate_detail_text(section, section_context)
                except Exception as exc:
                    # Debug-Hinweis:
                    # Wenn diese Meldung häufiger auftritt, temporär
                    # `st.write("offline:", is_offline())` und
                    # `st.write("openai_client vorhanden:", bool(st.session_state.get("openai_client")))`
                    # aktivieren, um den Zustand direkt im UI zu prüfen.
                    st.warning(f"⚠️ Details konnten nicht erzeugt werden: {exc}")
                    st.info("ℹ️ Bitte später erneut versuchen oder Offline-Modus prüfen.")
                    continue
                if supabase is not None:
                    try:
                        _save_cache_detail(
                            supabase,
                            cache_key,
                            section.key,
                            detail_text,
                            int(feedback_id) if feedback_id is not None else None,
                            fall_id,
                            feedback_mode,
                        )
                    except Exception as exc:
                        st.warning(f"⚠️ Schreiben des Detail-Caches fehlgeschlagen: {exc}")

            # Laufzeit-Cache immer aktualisieren.
            detail_cache_state[cache_key] = detail_text

            if from_supabase_cache:
                st.caption("♻️ Aus Supabase-Cache geladen (jünger als 3 Monate).")

            st.markdown(detail_text)
            detail_rendered_in_this_run = True

            # Öffnungs-Event nur bei *neuer* Aktivierung speichern.
            # Dadurch bleibt opened_at semantisch stabil und unnötige Supabase-Last
            # durch wiederholte Upserts bei normalen Reruns wird vermieden.
            if supabase is not None and feedback_id and selection_just_activated:
                try:
                    _save_open_event(supabase, int(feedback_id), section, detail_text)
                except Exception as exc:
                    st.warning(f"⚠️ Speichern des Öffnungs-Events fehlgeschlagen: {exc}")

        already_loaded = detail_cache_state.get(cache_key)
        if already_loaded and not detail_rendered_in_this_run:
            st.markdown(already_loaded)

        # Am Ende des Abschnitts wird der aktuelle Wert als "vorherige Auswahl"
        # persistiert, damit die Flankenerkennung im nächsten Run korrekt arbeitet.
        # Debug-Hinweis bei Bedarf:
        # st.write("Detail-Auswahl vorher/aktuell", previous_selection, selected)
        st.session_state[previous_selection_key] = selected
