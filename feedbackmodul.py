"""High-Level-Funktion zum Erzeugen des Feedbacks für die Studierenden."""

from typing import Callable, Optional

import streamlit as st

from module.MCP_Amboss import call_amboss_search
from module.patient_language import get_patient_forms
from module.offline import get_offline_feedback, is_offline
from module.feedback_pipeline import (
    FeedbackContext,
    combine_sections,
    preprocess_amboss_payload,
    run_feedback_pipeline,
)
from module.feedback_tasks import get_default_feedback_tasks
from module.amboss_summary import (
    loesche_zusammenfassung,
    speichere_zusammenfassung,
)


StatusUpdater = Callable[[str, str], None]
"""Typalias für optionale Statusmeldungen (Text, Status-Level)."""


def feedback_erzeugen(
    client,
    final_diagnose,
    therapie_vorschlag,
    user_ddx2,
    diagnostik_eingaben,
    gpt_befunde,
    koerper_befund,
    user_verlauf,
    anzahl_termine,
    diagnose_szenario,
    amboss_payload=None,
    *,
    patient_alter=None,
    status_updater: Optional[StatusUpdater] = None,
):
    """Erzeugt das Abschlussfeedback und kombiniert Teilabschnitte."""

    if is_offline():
        if status_updater:
            status_updater(
                "Offline-Modus aktiv – es wird ein statisches Feedback geladen.",
                "warning",
            )
        return get_offline_feedback(diagnose_szenario)

    patient_forms = get_patient_forms()

    # Hinweis: Der Parameter ``amboss_payload`` wird weiterhin akzeptiert,
    # damit bestehende Funktionsaufrufe unverändert bleiben. Die Verarbeitung
    # erfolgt jedoch immer mit der frisch abgerufenen MCP-Antwort, damit keine
    # Zwischenergebnisse zwischengespeichert werden.

    # Für jedes Feedback wird das MCP erneut befragt, damit keine veralteten
    # Zwischenergebnisse aus vorherigen Fällen übernommen werden.
    amboss_payload_live = None
    if diagnose_szenario:
        if status_updater:
            status_updater(
                "AMBOSS-MCP wird mit dem aktuellen Szenario abgefragt…",
                "info",
            )
        try:
            amboss_payload_live = call_amboss_search(query=diagnose_szenario)
            if status_updater:
                status_updater(
                    "AMBOSS-MCP hat Daten geliefert.",
                    "success",
                )
        except Exception as exc:  # pragma: no cover - reine Laufzeitfehler
            st.warning(
                "⚠️ Die AMBOSS-Schnittstelle konnte nicht abgefragt werden. "
                "Details können bei Bedarf über zusätzliche Debug-Ausgaben "
                "untersucht werden."
            )
            if status_updater:
                status_updater(
                    "AMBOSS-MCP konnte nicht erreicht werden.",
                    "warning",
                )
            # Debug-Hinweis: Für eine detaillierte Analyse kann
            # ``st.write('AMBOSS-Fehler:', exc)`` aktiviert werden.
    else:
        loesche_zusammenfassung()

    amboss_zusammenfassung = ""
    if amboss_payload_live:
        if status_updater:
            status_updater(
                "AMBOSS-Payload wird mit gpt-4o-mini zusammengefasst…",
                "info",
            )
        amboss_zusammenfassung = preprocess_amboss_payload(
            client,
            amboss_payload_live,
            diagnose_szenario,
            patient_alter,
        )
        if amboss_zusammenfassung:
            speichere_zusammenfassung(amboss_zusammenfassung)
            if status_updater:
                status_updater(
                    "AMBOSS-Zusammenfassung wurde erzeugt und gespeichert.",
                    "success",
                )
        else:
            loesche_zusammenfassung()
            if status_updater:
                status_updater(
                    "AMBOSS-Zusammenfassung blieb leer.",
                    "warning",
                )
    else:
        loesche_zusammenfassung()
        if status_updater:
            status_updater(
                "Keine AMBOSS-Daten verfügbar – es wird ohne Zusammenfassung fortgefahren.",
                "warning",
            )

    kontext = FeedbackContext(
        diagnose_szenario=diagnose_szenario,
        anzahl_termine=anzahl_termine,
        user_verlauf=user_verlauf,
        diagnostik_eingaben=diagnostik_eingaben,
        gpt_befunde=gpt_befunde,
        koerper_befund=koerper_befund,
        user_ddx2=user_ddx2,
        final_diagnose=final_diagnose,
        therapie_vorschlag=therapie_vorschlag,
        patient_forms_dativ=patient_forms.phrase("dat", article="indefinite"),
        patient_forms_genitiv=patient_forms.phrase("gen"),
        patient_alter=patient_alter,
        amboss_zusammenfassung=amboss_zusammenfassung,
    )

    # Alle Abschnitte werden parallel erzeugt, bleiben aber dank der Taskliste
    # in ihrer ursprünglichen Reihenfolge.
    if status_updater:
        status_updater("Parallele GPT-Feedbackaufträge werden gestartet…", "info")
    abschnitte = run_feedback_pipeline(
        client,
        kontext,
        tasks=get_default_feedback_tasks(),
        temperature=0.4,
    )

    if status_updater:
        status_updater("Alle Teilabschnitte wurden erfolgreich erzeugt.", "success")

    return combine_sections(abschnitte)
