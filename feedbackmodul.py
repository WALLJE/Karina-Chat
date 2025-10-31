"""High-Level-Funktion zum Erzeugen des Feedbacks für die Studierenden."""

from module.patient_language import get_patient_forms
from module.offline import get_offline_feedback, is_offline
from module.feedback_pipeline import (
    FeedbackContext,
    combine_sections,
    preprocess_amboss_payload,
    run_feedback_pipeline,
)
from module.feedback_tasks import get_default_feedback_tasks


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
):
    """Erzeugt das Abschlussfeedback und kombiniert Teilabschnitte."""

    if is_offline():
        return get_offline_feedback(diagnose_szenario)

    patient_forms = get_patient_forms()

    # Falls der AMBOSS-Modus aktiv ist, wird der Rohinhalt zuerst kompakt
    # zusammengefasst, damit die späteren Teilmodelle weniger Kontext verarbeiten
    # müssen.
    amboss_zusammenfassung = preprocess_amboss_payload(
        client,
        amboss_payload,
        diagnose_szenario,
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
        amboss_zusammenfassung=amboss_zusammenfassung,
    )

    # Alle Abschnitte werden parallel erzeugt, bleiben aber dank der Taskliste
    # in ihrer ursprünglichen Reihenfolge.
    abschnitte = run_feedback_pipeline(
        client,
        kontext,
        tasks=get_default_feedback_tasks(),
        temperature=0.4,
    )

    return combine_sections(abschnitte)
