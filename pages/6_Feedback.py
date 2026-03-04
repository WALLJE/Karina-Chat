"""Feedback-Seite der Simulation.

Diese Datei kapselt ausschließlich die Darstellung und Generierung des automatischen
Feedbacks nach Abschluss von Diagnose und Therapie. Die eigentliche Evaluation der
Studierenden erfolgt auf der nachgelagerten Seite `7_Evaluation_und_Download.py`.
"""

import streamlit as st

from diagnostikmodul import aktualisiere_diagnostik_zusammenfassung
from feedbackmodul import feedback_erzeugen
from module.footer import copyright_footer
from module.gpt_feedback import speichere_gpt_feedback_in_supabase
from module.feedback_detail import render_feedback_with_details
from module.loading_indicator import task_spinner
from module.navigation import redirect_to_start_page, render_next_page_link
from module.offline import display_offline_banner, is_offline
from module.sidebar import show_sidebar


# Die Sidebar und der Footer werden identisch zu den übrigen Seiten dargestellt, damit
# die Nutzerführung konsistent bleibt.
copyright_footer()
show_sidebar()
display_offline_banner()

def _sync_therapie_settings() -> None:
    """Synchronisiert persistierte Therapiesettings in den Session-State.

    Streamlit entfernt Widget-States, sobald das zugehörige Widget nicht mehr
    gerendert wird. Dadurch gehen Werte aus Seite 4/5 auf der Feedback-Seite
    verloren. Wir lesen die persistierten Keys und setzen die Standard-Keys
    erneut, damit Supabase-Speicherung und Feedback-Prompt vollständige Daten
    erhalten.
    """

    for key in ("therapie_setting_verdacht", "therapie_setting_final"):
        persist_key = f"{key}_persisted"
        if key not in st.session_state and persist_key in st.session_state:
            # Debug-Hinweis: Aktivieren, um den Sync nachvollziehen zu können.
            # st.write("Debug Seite 6 > Sync", key, "=", st.session_state[persist_key])
            st.session_state[key] = st.session_state[persist_key]


def _pruefe_voraussetzungen() -> None:
    """Validiert alle notwendigen Session-State-Einträge.

    Die Feedbackgenerierung setzt voraus, dass der Fall vollständig geladen wurde.
    Es wird absichtlich *nicht* auf Diagnose/Therapie geprüft, weil die Navigation
    diese Seite ohnehin nur freigibt, wenn beide Eingaben vorliegen. So vermeiden wir
    doppelte Abbruchbedingungen und erleichtern das Debugging.
    """

    if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
        redirect_to_start_page(
            "⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite."
        )


def _generiere_feedback() -> str:
    """Erzeugt oder lädt das finale Feedback aus dem Session-State.

    Falls noch kein Feedback existiert, werden alle für das LLM relevanten Daten
    zusammengetragen, anschließend erfolgt die Generierung – offline mit dem
    vorbereiteten Stub, online via OpenAI. Nach erfolgreicher Erstellung wird der
    Session-State aktualisiert und die Evaluation zurückgesetzt, sodass Studierende
    erneut Feedback abgeben können.
    """

    feedback_text = st.session_state.get("final_feedback", "").strip()
    if feedback_text:
        return feedback_text

    # Debug-Hinweis (beschriftet): Zusätzliche Prüfung, ob die Keys im
    # Session-State überhaupt existieren, bevor Werte gelesen werden.
    # TODO: Debug-Ausgaben später entfernen.
    # st.write(
    #     "Debug Seite 6 > Keys vorhanden (therapie_setting_*):",
    #     [key for key in st.session_state.keys() if "therapie_setting" in key],
    # )
    # st.write(
    #     "Debug Seite 6 > Key vorhanden verdacht?:",
    #     "therapie_setting_verdacht" in st.session_state,
    # )
    # st.write(
    #     "Debug Seite 6 > Key vorhanden final?:",
    #     "therapie_setting_final" in st.session_state,
    # )

    diagnostik_eingaben = st.session_state.get("diagnostik_eingaben_kumuliert", "")
    gpt_befunde = st.session_state.get("gpt_befunde_kumuliert", "")
    koerper_befund = st.session_state.get("koerper_befund", "")
    final_diagnose = st.session_state.get("final_diagnose", "")
    therapie_vorschlag = st.session_state.get("therapie_vorschlag", "")
    diagnose_szenario = st.session_state.get("diagnose_szenario", "")
    user_ddx2 = st.session_state.get("user_ddx2", "")
    user_verlauf = "\n".join(
        msg["content"] for msg in st.session_state.get("messages", []) if msg["role"] == "user"
    )
    anzahl_termine = st.session_state.get("diagnostik_runden_gesamt", 1)
    # Das Versorgungssetting wird explizit ins GPT-Feedback gegeben, damit
    # ambulante Terminlogik und stationäre Kontexte korrekt bewertet werden.
    therapie_setting_verdacht = st.session_state.get("therapie_setting_verdacht", "")
    therapie_setting_final = st.session_state.get("therapie_setting_final", "")
    # Debug-Hinweis (beschriftet): Aktivieren, um den Übergang von Seite 4/5
    # zur Feedback-Seite zu prüfen. Damit sieht man, ob die Settings im
    # Session-State noch vorhanden sind, bevor der Prompt gebaut wird.
    # TODO: Debug-Ausgaben später entfernen.
    # st.write("Debug Seite 6 > Session verdacht (vor Prompt):", therapie_setting_verdacht)
    # st.write("Debug Seite 6 > Session final (vor Prompt):", therapie_setting_final)

    if is_offline():
        feedback = feedback_erzeugen(
            st.session_state.get("openai_client"),
            final_diagnose,
            therapie_vorschlag,
            user_ddx2,
            diagnostik_eingaben,
            gpt_befunde,
            koerper_befund,
            user_verlauf,
            anzahl_termine,
            diagnose_szenario,
            therapie_setting_verdacht,
            therapie_setting_final,
        )
        st.session_state.final_feedback = feedback
    else:
        ladeaufgaben = [
            "Sammle relevante Falldaten",
            "Analysiere Antworten der Studierenden",
            "Formuliere individualisiertes Feedback",
        ]
        with task_spinner("⏳ Abschluss-Feedback wird erstellt...", ladeaufgaben) as indikator:
            indikator.advance(1)
            feedback = feedback_erzeugen(
                st.session_state["openai_client"],
                final_diagnose,
                therapie_vorschlag,
                user_ddx2,
                diagnostik_eingaben,
                gpt_befunde,
                koerper_befund,
                user_verlauf,
                anzahl_termine,
                diagnose_szenario,
                therapie_setting_verdacht,
                therapie_setting_final,
            )
            indikator.advance(1)
            st.session_state.final_feedback = feedback
            indikator.advance(1)
    st.session_state["student_evaluation_done"] = False
    st.session_state.pop("feedback_row_id", None)
    return feedback


def _zeige_feedback(feedback_text: str) -> None:
    """Stellt das Feedback dar und synchronisiert Supabase bei Bedarf."""

    if is_offline():
        st.info("🔌 Offline-Modus: Feedback wird nicht in Supabase gespeichert.")
    elif "feedback_row_id" not in st.session_state:
        # Sobald das Feedback erstmals angezeigt wird, erfolgt das Persistieren.
        speichere_gpt_feedback_in_supabase()

    st.subheader("📋 KI-generiertes Feedback")
    # Das kompakte Feedback bleibt der Standard. Die Detailtiefe wird erst
    # nach Klick je Unterpunkt geladen (token-sparsam, didaktisch gestuft).
    render_feedback_with_details(feedback_text)


def main() -> None:
    """Zentrale Steuermethode für die Feedback-Seite."""

    _sync_therapie_settings()

    # TODO: Debug-Ausgaben später entfernen.
    # st.write("Debug Seite 6 > Session-Keys (Start):", sorted(st.session_state.keys()))
    # st.write(
    #     "Debug Seite 6 > therapie_setting-Keys (Start):",
    #     [key for key in st.session_state.keys() if "therapie_setting" in key],
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot-Keys (Start):",
    #     [key for key in st.session_state.keys() if "debug_snapshot_therapie_setting" in key],
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot verdacht (Start):",
    #     st.session_state.get("debug_snapshot_therapie_setting_verdacht"),
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot final (Start):",
    #     st.session_state.get("debug_snapshot_therapie_setting_final"),
    # )

    _pruefe_voraussetzungen()
    aktualisiere_diagnostik_zusammenfassung()

    if "student_evaluation_done" not in st.session_state:
        st.session_state["student_evaluation_done"] = False

    feedback_text = _generiere_feedback()
    if not feedback_text:
        st.error("🚫 Das Abschluss-Feedback konnte nicht erstellt werden.")
        st.stop()

    _zeige_feedback(feedback_text)

    # TODO: Debug-Ausgaben später entfernen.
    # st.write("Debug Seite 6 > Session-Keys (Ende):", sorted(st.session_state.keys()))
    # st.write(
    #     "Debug Seite 6 > therapie_setting-Keys (Ende):",
    #     [key for key in st.session_state.keys() if "therapie_setting" in key],
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot-Keys (Ende):",
    #     [key for key in st.session_state.keys() if "debug_snapshot_therapie_setting" in key],
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot verdacht (Ende):",
    #     st.session_state.get("debug_snapshot_therapie_setting_verdacht"),
    # )
    # st.write(
    #     "Debug Seite 6 > Snapshot final (Ende):",
    #     st.session_state.get("debug_snapshot_therapie_setting_final"),
    # )

    st.markdown("---")
    render_next_page_link(
        "pages/7_Evaluation_und_Download.py",
        label="Weiter zur Evaluation",
        icon="📊",
        helper_text="💡 Die Evaluation ist für die Weiterentwicklung und wissenschaftliche Auswertung extrem wichtig.",
    )


if __name__ == "__main__":  # pragma: no cover - Streamlit startet die Seite selbst
    main()
