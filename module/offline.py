import streamlit as st


def is_offline() -> bool:
    """Return True if the application runs without OpenAI connectivity."""
    return bool(st.session_state.get("offline_mode", False))


def display_offline_banner() -> None:
    """Show a prominent banner while the offline mode is active."""
    if is_offline():
        st.warning(
            "🔌 Offline-Modus aktiv: Antworten stammen aus statischen Platzhaltern. "
            "Es werden keine OpenAI-Anfragen gesendet und keine Tokens gezählt."
        )


def get_offline_patient_reply(patient_name: str) -> str:
    """Provide a short canned answer for the anamnesis chat while offline."""
    name = patient_name or "Die simulierte Patientin"
    return (
        "(Offline) {name} antwortet ruhig:"\
        .format(name=name)
        + "\n"
        + "Ich kann dir derzeit nur die Basisinformationen aus dem Szenario schildern. "
          "Bitte prüfe den Steckbrief und die bisherigen Notizen, bis der Online-Modus wieder aktiv ist."
    )


def get_offline_koerperbefund() -> str:
    """Return a generic but plausible examination report for offline usage."""
    return (
        "🔌 Offline-Modus – standardisierter Befund"\
        "\n\n"
        "**Allgemeinzustand:** wach, orientiert, kooperativ; Vitalparameter im Normbereich."\
        "\n**Abdomen:** weich, kein Druckschmerz, Darmgeräusche regelrecht."\
        "\n**Auskultation Herz/Lunge:** Herztöne rein, rhythmisch; Vesikuläratmen beidseits ohne Nebengeräusche."\
        "\n**Haut:** rosig, warm, keine Auffälligkeiten."\
        "\n**Extremitäten:** frei beweglich, keine Ödeme, periphere Pulse tastbar."
    )


def get_offline_befund(neue_diagnostik: str) -> str:
    """Build a placeholder diagnostics report while offline."""
    angefordert = neue_diagnostik.strip() or "(keine zusätzlichen Angaben gemacht)"
    return (
        "🔌 Offline-Modus – vereinfachter Befundbericht"\
        "\n\n"
        f"Angeforderte Untersuchungen:\n{angefordert}\n\n"
        "Ergebnisse (statisch generiert):\n"
        "- Laborwerte im Referenzbereich, keine pathologischen Abweichungen.\n"
        "- Bildgebung ohne richtungsweisende Befunde.\n"
        "- Funktionsdiagnostik unauffällig."
    )


def get_offline_feedback(diagnose_szenario: str) -> str:
    """Provide a static feedback note while offline."""
    szenario = diagnose_szenario or "dem aktuellen Szenario"
    return (
        "🔌 Offline-Modus – kein automatisches GPT-Feedback verfügbar."\
        "\n"
        f"Bewerte deine Bearbeitung von {szenario} anhand der Checkliste:"
        "\n1. Wurden die relevanten Anamnesepunkte erfragt?"
        "\n2. Passten Diagnostik und Differentialdiagnosen zusammen?"
        "\n3. Ist die finale Diagnose nachvollziehbar und das Therapiekonzept begründet?"
        "\nNutze die Lösungen oder besprich den Fall im Team, sobald der Online-Modus wieder aktiv ist."
    )


def get_offline_sprachcheck(text_input: str) -> str:
    """Return the original text when no correction can be generated."""
    return text_input
