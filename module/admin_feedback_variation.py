"""Hilfsfunktionen für wiederholte GPT-Feedback-Durchläufe im Adminbereich.

Die Funktionen in diesem Modul sind bewusst umfangreich kommentiert, damit
Administrierende die einzelnen Schritte nachvollziehen und bei Bedarf
anpassen können. Alle Abläufe sind strikt auf den Admin-Modus beschränkt und
verändern keine Nutzungswege im regulären Betrieb.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import textwrap
import uuid
from typing import Dict, Iterable, List, Tuple

import streamlit as st
from fpdf import FPDF
from supabase import Client, create_client

from feedbackmodul import feedback_erzeugen
from module.feedback_mode import (
    FEEDBACK_MODE_AMBOSS_CHATGPT,
    FEEDBACK_MODE_CHATGPT,
    SESSION_KEY_EFFECTIVE_MODE,
    reset_random_mode,
    set_mode_override,
)
from module.llm_state import ensure_llm_client
from module.offline import is_offline

# Name der Supabase-Tabelle, in der die wiederholten Feedback-Durchläufe
# gespeichert werden. Der SQL-Entwurf befindet sich in der README und kann bei
# Bedarf in der Supabase-Konsole ausgeführt werden.
_TABLE_VARIATIONS = "feedback_gpt_variationen"

# Liste der Feldnamen aus der Tabelle ``feedback_gpt``, die für das erneute
# Erzeugen des Feedbacks benötigt werden. Die Keys werden im Admin-UI
# angezeigt, falls Werte fehlen oder leer sind, damit gezielt nachgepflegt
# werden kann.
_REQUIRED_FIELDS: Dict[str, str] = {
    "szenario": "diagnose_szenario",
    "chatverlauf": "user_verlauf",
    "diagnostik": "diagnostik_eingaben_kumuliert",
    "befunde": "gpt_befunde_kumuliert",
    "verdachtsdiagnosen": "user_ddx2",
    "finale_diagnose": "final_diagnose",
    "therapie": "therapie_vorschlag",
}

# Optionale Felder ergänzen den Kontext, sind für den Prompt aber nicht
# zwingend notwendig. Sie werden, wenn vorhanden, in den Session-State
# übernommen, fehlen ansonsten aber ohne Abbruch – ein Hinweis wird dennoch
# ausgegeben, damit die Datengrundlage bewertet werden kann.
_OPTIONAL_FIELDS: Dict[str, str] = {
    "geschlecht": "patient_gender",
    "alter": "patient_age",
    "diagnostik_runden_gesamt": "diagnostik_runden_gesamt",
    "koerper_befund": "koerper_befund",
}

# Feste Schriftart mit Unicode-Unterstützung, damit Sonderzeichen wie "₂"
# sauber gerendert werden. Sollte der Font auf dem System fehlen, wird eine
# klare Fehlermeldung ausgegeben, damit Admins gezielt nachrüsten können.
_PDF_FONT_NAME = "DejaVuSans"
_PDF_FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


class FeedbackVariationError(RuntimeError):
    """Spezifische Exception für Fehler im Evaluationsablauf."""


@dataclass
class FeedbackCaseData:
    """Bündelt alle Informationen eines gespeicherten Feedback-Eintrags."""

    id: int
    szenario: str
    datum: str | None
    rohwerte: Dict[str, object]
    fehlende_felder: List[str]


@dataclass
class FeedbackRunResult:
    """Speichert das Ergebnis eines einzelnen Durchlaufs."""

    laufgruppe: uuid.UUID
    lauf_index: int
    modus: str
    feedback_text: str
    feedback_id: int
    szenario: str
    fall_datum: str | None
    fehlende_variablen: List[str]


def _get_supabase_client() -> Client:
    """Stellt einen authentifizierten Supabase-Client bereit.

    Der Zugriff basiert auf den Einträgen in ``st.secrets['supabase']``. Alle
    relevanten Fehlermeldungen werden auf Deutsch formuliert, damit Admins bei
    der Einrichtung schnell nachvollziehen können, welche Angaben fehlen.
    """

    supabase_config = st.secrets.get("supabase")
    if not supabase_config:
        raise FeedbackVariationError("Supabase-Konfiguration fehlt in st.secrets.")

    try:
        url = supabase_config["url"]
        key = supabase_config["key"]
    except KeyError as exc:
        raise FeedbackVariationError("Supabase-Zugangsdaten sind unvollständig.") from exc

    try:
        return create_client(url, key)
    except Exception as exc:  # pragma: no cover - Netzwerkaussetzer schwer zu simulieren
        raise FeedbackVariationError(f"Supabase-Verbindung fehlgeschlagen: {exc!r}") from exc


def lade_feedback_fall(fall_id: int) -> FeedbackCaseData:
    """Lädt einen Datensatz aus ``feedback_gpt`` anhand der ID.

    Args:
        fall_id: Die ``ID`` des vorhandenen Feedback-Datensatzes.

    Returns:
        FeedbackCaseData mit Rohwerten und Hinweisen auf fehlende Felder.
    """

    client = _get_supabase_client()
    try:
        response = (
            client.table("feedback_gpt").select("*").eq("ID", fall_id).limit(1).execute()
        )
    except Exception as exc:  # pragma: no cover - defensive Absicherung
        raise FeedbackVariationError(
            f"Abruf des Feedback-Datensatzes fehlgeschlagen: {exc!r}"
        ) from exc

    if getattr(response, "error", None):
        raise FeedbackVariationError(f"Supabase meldet einen Fehler: {response.error}")

    rows: Iterable[Dict[str, object]] = response.data or []
    if not rows:
        raise FeedbackVariationError("Kein Datensatz mit dieser ID gefunden.")

    row = dict(rows[0])
    fehlende_felder: List[str] = []

    for column in list(_REQUIRED_FIELDS) + list(_OPTIONAL_FIELDS):
        wert = row.get(column)
        if wert in (None, ""):
            fehlende_felder.append(column)

    szenario = str(row.get("szenario", "")).strip()
    datum = row.get("datum")

    if not szenario:
        fehlende_felder.append("szenario")

    return FeedbackCaseData(
        id=int(row.get("ID", fall_id)),
        szenario=szenario,
        datum=str(datum) if datum is not None else None,
        rohwerte=row,
        fehlende_felder=fehlende_felder,
    )


def _extrahiere_user_verlauf(chatverlauf: str, patientenname: str) -> str:
    """Filtert den gespeicherten Chatverlauf auf Nutzer:innen-Beiträge.

    Der ursprüngliche Export aus ``module.gpt_feedback`` markiert Nutzerfragen
    mit dem Präfix ``"Du:"`` und versieht alle übrigen Zeilen mit dem
    jeweils verwendeten Patientennamen. Diese Funktion streicht daher alle
    Zeilen, die nicht eindeutig als Nutzereingabe erkennbar sind. So wird beim
    erneuten Feedback-Lauf derselbe Input wie im Live-Betrieb genutzt.

    Für Debugging kann der Rückgabewert über ``st.write`` inspiziert werden,
    falls in historischen Datensätzen ungewöhnliche Präfixe auftauchen.
    """

    if not chatverlauf:
        return ""

    nutzerzeilen: List[str] = []
    patientenname = patientenname.strip()

    for zeile in chatverlauf.splitlines():
        bereinigt = zeile.strip()
        if not bereinigt:
            continue

        sprecher, trenner, inhalt = bereinigt.partition(":")
        if not trenner:
            # Falls alte Datensätze kein Präfix haben, hilft eine temporäre
            # ``st.write(bereinigt)``-Ausgabe, um ein passendes Muster zu
            # ergänzen. Standardmäßig wird diese Zeile übersprungen, damit
            # keine Patienten- oder Systemtexte in den Prompt geraten.
            continue

        sprecher_klein = sprecher.strip().lower()
        if sprecher_klein in {"du", "user", "studierende", "studierender"}:
            nutzerzeilen.append(inhalt.strip())
        elif patientenname and sprecher.strip() == patientenname:
            # Patientenantworten werden bewusst ignoriert, damit der Prompt
            # unverändert nur die Nutzereingaben enthält.
            continue

    return "\n".join(nutzerzeilen).strip()


def _uebernehme_in_session_state(rohwerte: Dict[str, object]) -> None:
    """Überträgt die geladenen Felder in den Session-State.

    Der Session-State wird bewusst nur für die benötigten Schlüssel gefüllt,
    damit der restliche Admin-Bereich unbeeinflusst bleibt. Ergänzende
    Debug-Hinweise lassen sich bei Bedarf aktivieren, indem in dieser Funktion
    temporär ``st.write(rohwerte)`` eingebaut wird.
    """

    patientenname = str(rohwerte.get("name", "")).strip() or "Patient"
    chatverlauf_roh = str(rohwerte.get("chatverlauf", "")).strip()
    user_chatverlauf = _extrahiere_user_verlauf(chatverlauf_roh, patientenname)

    # Falls keine Nutzerzeilen erkannt werden, wird der Verlauf bewusst NICHT
    # automatisch ergänzt, damit der Prompt nicht versehentlich Patientenant-
    # worten enthält. Über eine temporäre ``st.write(chatverlauf_roh)``-
    # Ausgabe können Admins das Rohformat analysieren und bei Bedarf das
    # Präfix-Set in ``_extrahiere_user_verlauf`` erweitern. Ein expliziter
    # Hinweis macht auf die leere Eingabe aufmerksam, sodass der Datensatz
    # vor dem erneuten Feedbacklauf bereinigt werden kann.
    if not user_chatverlauf and chatverlauf_roh:
        st.warning(
            "⚠️ Im gespeicherten Chatverlauf wurden keine eindeutigen Nutzer:innen-Zeilen gefunden. "
            "Bitte Präfixe prüfen und ggf. anpassen."
        )

    for spaltenname, state_key in _REQUIRED_FIELDS.items():
        wert = rohwerte.get(spaltenname, "") or ""
        if spaltenname == "chatverlauf":
            wert = user_chatverlauf
        st.session_state[state_key] = wert

    # Historische Keys aus dem normalen Feedback-Modul werden zusätzlich
    # gepflegt, damit andere Hilfsfunktionen weiterhin funktionieren, falls sie
    # im Adminbereich aufgerufen werden.
    st.session_state["diagnostik_eingaben"] = st.session_state.get(
        "diagnostik_eingaben_kumuliert", ""
    )
    st.session_state["gpt_befunde"] = st.session_state.get(
        "gpt_befunde_kumuliert", ""
    )

    for spaltenname, state_key in _OPTIONAL_FIELDS.items():
        st.session_state[state_key] = rohwerte.get(spaltenname, "") or ""

    # Damit der Gesprächsverlauf vom Feedback-Prompt erkannt wird, wird er als
    # einzige Nutzer-Nachricht in ``st.session_state.messages`` hinterlegt.
    st.session_state["messages"] = [
        {"role": "user", "content": abschnitt}
        for abschnitt in user_chatverlauf.split("\n")
        if abschnitt.strip()
    ]

    # Für die erneute Berechnung wird das finale Feedback bewusst entfernt.
    st.session_state.pop("final_feedback", None)


def _setze_feedback_modus(modus: str) -> None:
    """Legt den gewünschten Feedback-Modus fest und verhindert Zufallswechsel."""

    set_mode_override(modus)
    reset_random_mode()
    st.session_state[SESSION_KEY_EFFECTIVE_MODE] = modus


def _splitte_lange_tokens(text: str, max_tokenlaenge: int = 60) -> str:
    """Zerschneidet extrem lange Wörter, damit ``multi_cell`` nicht scheitert.

    Die FPDF-Fehlermeldung "Not enough horizontal space to render a single
    character" tritt auf, wenn ein einzelnes, untrennbares Token breiter ist als
    der verfügbare Zellenraum. Diese Hilfsfunktion flicht nach ``max_tokenlaenge``
    Zeichen Leerzeichen ein, sodass FPDF das Wort sauber umbrechen kann. Die
    originale Zeichenfolge bleibt dabei visuell gut lesbar, ein möglicher
    Minimalverlust (fehlende Silbentrennung) ist für die Auswertung unerheblich.
    """

    def _teile_token(token: str) -> str:
        if len(token) <= max_tokenlaenge:
            return token
        # Die Wortteile werden mit Leerzeichen verbunden, damit FPDF einen
        # Umbruchpunkt erkennt. Bei Bedarf kann das Limit über den Parameter
        # ``max_tokenlaenge`` variiert werden.
        return " ".join(
            token[i : i + max_tokenlaenge]
            for i in range(0, len(token), max_tokenlaenge)
        )

    segmente = re.split(r"(\s+)", text)
    return "".join(_teile_token(segment) if segment and not segment.isspace() else segment for segment in segmente)


def _wrap_for_pdf(text: str, breite_zeichen: int = 95) -> str:
    """Formatiert Text für ``multi_cell`` und bricht lange Wörter um.

    Neben dem klassischen Zeilenumbruch per ``textwrap.fill`` werden extrem
    lange Tokens vorab künstlich getrennt. Das verhindert zuverlässig den
    bekannten FPDF-Abbruch. Für Debugging kann temporär ``st.write(text)``
    aufgerufen werden, um zu prüfen, welcher Text hier ankommt.
    """

    if not text:
        return ""

    text = _splitte_lange_tokens(str(text))

    def _umbruch(block: str) -> str:
        return textwrap.fill(
            block.strip(),
            width=breite_zeichen,
            break_long_words=True,
            break_on_hyphens=False,
        )

    saubere_abschnitte: List[str] = []
    for abschnitt in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not abschnitt.strip():
            saubere_abschnitte.append("")
            continue
        saubere_abschnitte.append(_umbruch(abschnitt))

    return "\n".join(saubere_abschnitte)


def _setze_unicode_font(pdf: FPDF, groesse: int = 12) -> None:
    """Aktiviert eine Unicode-Schriftart, die auch Sonderzeichen rendern kann.

    Der Fehler "Character ... is outside the range of characters supported by the"
    " font used" tritt auf, wenn der Standard-Helvetica-Font auf ein nicht
    unterstütztes Zeichen trifft (z. B. Tiefstellungen wie "₂"). Durch das
    Hinterlegen eines TrueType-Fonts mit Unicode-Unterstützung (DejaVuSans) wird
    dieser Engpass eliminiert. Falls der Font im Deployment fehlt, erhält die
    Admin-Oberfläche eine klare Fehlermeldung. Für tiefere Analysen kann temporär
    ``st.write(pdf.fonts)`` aktiviert werden, um den Font-Cache einzusehen.
    """

    if not _PDF_FONT_PATH.exists():
        raise FeedbackVariationError(
            "Unicode-Font nicht gefunden. Bitte installiere die Paketquelle "
            "'ttf-dejavu' oder hinterlege den Font unter "
            f"{_PDF_FONT_PATH}."
        )

    # add_font ist idempotent – wir prüfen dennoch den Cache, um die Fehlermeldung
    # "Font already added" zu vermeiden und die Logs sauber zu halten.
    if _PDF_FONT_NAME not in pdf.fonts:
        try:
            pdf.add_font(_PDF_FONT_NAME, "", str(_PDF_FONT_PATH), uni=True)
        except RuntimeError as exc:
            raise FeedbackVariationError(
                "Unicode-Font konnte nicht geladen werden. Bitte prüfe den Pfad "
                "und die Dateiberechtigungen."
            ) from exc

    pdf.set_font(_PDF_FONT_NAME, size=groesse)


def _erstelle_pdf(laufgruppe: uuid.UUID, ergebnisse: List[FeedbackRunResult]) -> bytes:
    """Erzeugt ein PDF, in dem jedes Feedback auf einer eigenen Seite steht."""

    pdf = FPDF(format="A4")
    # Breite Ränder plus automatischer Seitenumbruch reduzieren die Gefahr,
    # dass untrennbare Wörter den verfügbaren Platz überschreiten. Sollte es
    # dennoch klemmen, kann testweise der Margin erhöht oder der Text über
    # ``st.write`` inspiziert werden (siehe Debug-Hinweise oben).
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Explizite Breitenberechnung in Millimetern: Dadurch wird vermieden, dass
    # sich ein verschobener X-Offset aus vorigen Zellen auf nachfolgende
    # Breitenberechnungen auswirkt. Der Wert orientiert sich an A4 mit 15 mm
    # Rand: 210 mm - 15 mm - 15 mm = 180 mm.
    zellenbreite = pdf.w - pdf.l_margin - pdf.r_margin

    titel = f"Feedback-Lauf {laufgruppe}"  # Modus wird bewusst nicht ausgegeben.

    for ergebnis in ergebnisse:
        pdf.add_page()
        # Unicode-fähige Schrift aktivieren, damit Sonderzeichen wie "₂" oder
        # mathematische Symbole nicht zum Abbruch führen.
        _setze_unicode_font(pdf, groesse=12)
        pdf.multi_cell(zellenbreite, 8, _wrap_for_pdf(titel))
        pdf.ln(2)
        pdf.multi_cell(zellenbreite, 8, _wrap_for_pdf(f"Fall-ID: {ergebnis.feedback_id}"))
        pdf.multi_cell(zellenbreite, 8, _wrap_for_pdf(f"Datum: {datetime.now():%d.%m.%Y}"))
        pdf.multi_cell(zellenbreite, 8, _wrap_for_pdf(f"Durchlauf: {ergebnis.lauf_index}"))
        pdf.ln(4)
        _setze_unicode_font(pdf, groesse=11)
        pdf.multi_cell(zellenbreite, 6, _wrap_for_pdf(f"Szenario: {ergebnis.szenario or 'unbekannt'}"))
        pdf.ln(2)
        pdf.multi_cell(zellenbreite, 6, _wrap_for_pdf(ergebnis.feedback_text))

    # Rückgabe erfolgt als Bytes. fpdf2 liefert bei ``dest="S"`` seit Version
    # 2.7 standardmäßig ein ``bytearray``. Falls in älteren Umgebungen noch ein
    # ``bytes``- oder ``str``-Objekt zurückkommt, wandeln wir das Ergebnis
    # defensiv um und geben eine klare Fehlermeldung aus, statt stumm eine
    # AttributeError zu produzieren. Für Debugging kann testweise
    # ``st.write(type(roh_output), len(roh_output))`` aktiviert werden, um den
    # Rückgabetyp im konkreten Deployment sichtbar zu machen.
    roh_output = pdf.output(dest="S")

    if isinstance(roh_output, bytearray):
        return bytes(roh_output)

    if isinstance(roh_output, bytes):
        return roh_output

    if isinstance(roh_output, str):
        # fpdf1 gab hier einen latin-1-kodierten String zurück. Wir übernehmen
        # dieses Mapping explizit, damit historische Deployments weiterhin
        # funktionieren, und lassen bei nicht abbildbaren Zeichen bewusst einen
        # Fehler zu, statt still etwas abzuschneiden.
        return roh_output.encode("latin-1")

    raise FeedbackVariationError(
        "Unerwarteter Rückgabetyp beim PDF-Export. Bitte fpdf-Version prüfen."
    )


def fuehre_feedback_durchlaeufe_aus(
    fall: FeedbackCaseData,
    durchlaeufe: int,
    modi: Iterable[str],
) -> Tuple[List[FeedbackRunResult], bytes]:
    """Startet mehrere Feedback-Berechnungen für denselben Fall.

    Args:
        fall: Geladener Datensatz aus ``feedback_gpt``.
        durchlaeufe: Anzahl der Wiederholungen je Modus.
        modi: Iterable aus ``FEEDBACK_MODE_CHATGPT`` oder ``FEEDBACK_MODE_AMBOSS_CHATGPT``.

    Returns:
        Liste aller Ergebnisse sowie die PDF-Bytes mit den Feedbacks (ohne Modus).
    """

    if is_offline():
        raise FeedbackVariationError("Offline-Modus aktiv – GPT-Feedback kann nicht neu berechnet werden.")

    client = ensure_llm_client()
    if client is None:
        raise FeedbackVariationError("Kein GPT-Client verfügbar. Bitte API-Konfiguration prüfen.")

    laufgruppe = uuid.uuid4()
    ergebnisse: List[FeedbackRunResult] = []

    urspruenglicher_modus = st.session_state.get(SESSION_KEY_EFFECTIVE_MODE)
    urspruengliche_override = st.session_state.get("feedback_mode_override")

    _uebernehme_in_session_state(fall.rohwerte)

    for modus in modi:
        _setze_feedback_modus(modus)
        for index in range(1, durchlaeufe + 1):
            feedback_text = feedback_erzeugen(
                client,
                st.session_state.get("final_diagnose", ""),
                st.session_state.get("therapie_vorschlag", ""),
                st.session_state.get("user_ddx2", ""),
                st.session_state.get("diagnostik_eingaben_kumuliert", ""),
                st.session_state.get("gpt_befunde_kumuliert", ""),
                st.session_state.get("koerper_befund", ""),
                st.session_state.get("user_verlauf", ""),
                int(st.session_state.get("diagnostik_runden_gesamt", 1) or 1),
                st.session_state.get("diagnose_szenario", fall.szenario),
            )

            ergebnisse.append(
                FeedbackRunResult(
                    laufgruppe=laufgruppe,
                    lauf_index=index,
                    modus=modus,
                    feedback_text=feedback_text,
                    feedback_id=fall.id,
                    szenario=fall.szenario,
                    fall_datum=fall.datum,
                    fehlende_variablen=fall.fehlende_felder,
                )
            )

    # Ursprüngliche Moduseinstellungen werden wiederhergestellt, damit der
    # restliche Adminbereich unverändert weitergenutzt werden kann.
    if urspruengliche_override is None:
        set_mode_override(None)
    else:
        set_mode_override(urspruengliche_override)
    if urspruenglicher_modus:
        st.session_state[SESSION_KEY_EFFECTIVE_MODE] = urspruenglicher_modus

    pdf_bytes = _erstelle_pdf(laufgruppe, ergebnisse)
    return ergebnisse, pdf_bytes


def speichere_durchlaeufe_in_supabase(ergebnisse: List[FeedbackRunResult]) -> None:
    """Persistiert alle Durchläufe in der Tabelle ``feedback_gpt_variationen``."""

    if not ergebnisse:
        return

    client = _get_supabase_client()

    payload = [
        {
            "laufgruppe": str(e.laufgruppe),
            "feedback_id": e.feedback_id,
            "szenario": e.szenario,
            "fall_datum": e.fall_datum,
            "modus": e.modus,
            "lauf_index": e.lauf_index,
            "feedback_text": e.feedback_text,
            "fehlende_variablen": ", ".join(sorted(set(e.fehlende_variablen))) if e.fehlende_variablen else None,
        }
        for e in ergebnisse
    ]

    try:
        client.table(_TABLE_VARIATIONS).insert(payload).execute()
    except Exception as exc:  # pragma: no cover - Netzfehler schwer abbildbar
        raise FeedbackVariationError(
            f"Speichern der Feedback-Durchläufe fehlgeschlagen: {exc!r}"
        ) from exc


__all__ = [
    "FeedbackCaseData",
    "FeedbackRunResult",
    "FeedbackVariationError",
    "fuehre_feedback_durchlaeufe_aus",
    "lade_feedback_fall",
    "speichere_durchlaeufe_in_supabase",
]
