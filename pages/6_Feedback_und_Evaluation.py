import streamlit as st
from feedbackmodul import feedback_erzeugen
from module.feedback_ui import student_feedback
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.gpt_feedback import speichere_gpt_feedback_in_supabase
from diagnostikmodul import aktualisiere_diagnostik_zusammenfassung
from module.offline import display_offline_banner, is_offline
from module.amboss_config import sync_chatgpt_amboss_session_state

show_sidebar()
copyright_footer()
display_offline_banner()

# Voraussetzungen prüfen
if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
    st.warning("⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite.")
    st.page_link("Karina_Chat_2.py", label="⬅ Zur Startseite")
    st.stop()

#if not st.session_state.get("final_diagnose") or not st.session_state.get("therapie_vorschlag"):
#    st.warning("⚠️ Bitte zuerst Diagnose und Therapie eingeben.")
#    st.stop()

aktualisiere_diagnostik_zusammenfassung()
chatgpt_amboss_aktiv = sync_chatgpt_amboss_session_state()

if "student_evaluation_done" not in st.session_state:
    st.session_state["student_evaluation_done"] = False

feedback_text = st.session_state.get("final_feedback", "").strip()

if chatgpt_amboss_aktiv and st.session_state.get("is_admin") and st.session_state.get("amboss_result"):
    with st.expander("AMBOSS JSON-Datei", expanded=False):
        st.json(st.session_state.get("amboss_result"))
    amboss_summary_text = st.session_state.get("amboss_summary")
    if amboss_summary_text:
        with st.expander("AMBOSS-Zusammenfassung (gpt-4o-mini)", expanded=False):
            st.markdown(amboss_summary_text)
    else:
        st.info("ℹ️ Noch keine GPT-Zusammenfassung des AMBOSS-Payloads verfügbar.")
elif st.session_state.get("is_admin") and not chatgpt_amboss_aktiv:
    st.info(
        "ℹ️ Die ChatGPT+AMBOSS-Funktion ist aktuell deaktiviert. "
        "Aktiviere sie im Adminbereich, um die MCP-Daten einzusehen."
    )

if not feedback_text:
    # Debug-Hinweis (beschriftet): Zusätzliche Prüfung, ob die Keys im
    # Session-State überhaupt existieren, bevor Werte gelesen werden.
    st.write(
        "Debug Seite 6E > Keys vorhanden (therapie_setting_*):",
        [key for key in st.session_state.keys() if "therapie_setting" in key],
    )
    st.write(
        "Debug Seite 6E > Key vorhanden verdacht?:",
        "therapie_setting_verdacht" in st.session_state,
    )
    st.write(
        "Debug Seite 6E > Key vorhanden final?:",
        "therapie_setting_final" in st.session_state,
    )
    diagnostik_eingaben = st.session_state.get("diagnostik_eingaben_kumuliert", "")
    gpt_befunde = st.session_state.get("gpt_befunde_kumuliert", "")
    koerper_befund = st.session_state.get("koerper_befund", "")
    final_diagnose = st.session_state.get("final_diagnose", "")
    therapie_vorschlag = st.session_state.get("therapie_vorschlag", "")
    diagnose_szenario = st.session_state.get("diagnose_szenario", "")
    user_ddx2 = st.session_state.get("user_ddx2", "")
    user_verlauf = "\n".join([
        msg["content"] for msg in st.session_state.messages
        if msg["role"] == "user"
    ])
    anzahl_termine = st.session_state.get("diagnostik_runden_gesamt", 1)
    # Versorgungssetting wird für das Feedback separat übergeben, damit
    # ambulante und stationäre Kontexte korrekt bewertet werden können.
    therapie_setting_verdacht = st.session_state.get("therapie_setting_verdacht", "")
    therapie_setting_final = st.session_state.get("therapie_setting_final", "")
    # Debug-Hinweis (beschriftet): Aktivieren, um den Übergang von Seite 4/5
    # zur kombinierten Feedback/Evaluation-Seite zu prüfen. So sieht man, ob
    # die Settings im Session-State noch vorhanden sind, bevor der Prompt
    # gebaut wird.
    st.write("Debug Seite 6E > Session verdacht (vor Prompt):", therapie_setting_verdacht)
    st.write("Debug Seite 6E > Session final (vor Prompt):", therapie_setting_final)

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
            therapie_setting_verdacht=therapie_setting_verdacht,
            therapie_setting_final=therapie_setting_final,
            amboss_payload=st.session_state.get("amboss_result"),
            patient_alter=st.session_state.get("patient_age"),
        )
    else:
        if st.session_state.get("is_admin"):
            status_container = st.container()
            status_eintraege = []

            def status_updater(text: str, status: str = "info") -> None:
                emoji_map = {
                    "info": "ℹ️",
                    "success": "✅",
                    "warning": "⚠️",
                    "error": "❌",
                }
                emoji = emoji_map.get(status, "ℹ️")
                status_eintraege.append(f"{emoji} {text}")
                status_container.markdown("\n\n".join(status_eintraege))

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
                therapie_setting_verdacht=therapie_setting_verdacht,
                therapie_setting_final=therapie_setting_final,
                amboss_payload=st.session_state.get("amboss_result"),
                patient_alter=st.session_state.get("patient_age"),
                status_updater=status_updater,
            )
            status_updater("Abschlussfeedback erfolgreich erstellt.", "success")
        else:
            with st.spinner("⏳ Abschluss-Feedback wird erstellt..."):
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
                    therapie_setting_verdacht=therapie_setting_verdacht,
                    therapie_setting_final=therapie_setting_final,
                    amboss_payload=st.session_state.get("amboss_result"),
                    patient_alter=st.session_state.get("patient_age"),
                )

    st.session_state.final_feedback = feedback
    st.session_state["student_evaluation_done"] = False
    st.session_state.pop("feedback_row_id", None)
    feedback_text = feedback
    st.success("✅ Evaluation erstellt")
    if is_offline():
        st.info("🔌 Offline-Modus: Es wurde ein statisches Feedback verwendet.")

if feedback_text:
    if is_offline():
        st.info("🔌 Offline-Modus: Feedback wird nicht in Supabase gespeichert.")
    elif "feedback_row_id" not in st.session_state:
        speichere_gpt_feedback_in_supabase()

    st.markdown(feedback_text)
else:
    st.error("🚫 Das Abschluss-Feedback konnte nicht erstellt werden.")
    st.stop()

if st.session_state.final_feedback:
    student_feedback()

st.markdown("---")
st.subheader("📄 Download")

if st.session_state.get("final_feedback") and st.session_state.get("student_evaluation_done"):
    protokoll = ""

    protokoll += f"Simuliertes Krankheitsbild: {st.session_state.diagnose_szenario}\n\n"

    protokoll += "---\n💬 Gesprächsverlauf (nur Fragen des Studierenden):\n"
    for msg in st.session_state.messages[1:]:
        rolle = st.session_state.patient_name if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n"

    if "koerper_befund" in st.session_state:
        protokoll += "\n---\n Körperlicher Untersuchungsbefund:\n"
        protokoll += st.session_state.koerper_befund + "\n"

    if "user_ddx2" in st.session_state:
        protokoll += "\n---\n Erhobene Differentialdiagnosen:\n"
        protokoll += st.session_state.user_ddx2 + "\n"

    if "diagnostik_eingaben_kumuliert" in st.session_state:
        protokoll += "\n---\n Geplante diagnostische Maßnahmen (alle Termine):\n"
        protokoll += st.session_state.diagnostik_eingaben_kumuliert + "\n"

    if "gpt_befunde_kumuliert" in st.session_state:
        protokoll += "\n---\n📄 Ergebnisse der diagnostischen Maßnahmen:\n"
        protokoll += st.session_state.gpt_befunde_kumuliert + "\n"

    if "final_diagnose" in st.session_state:
        protokoll += "\n---\n Finale Diagnose:\n"
        protokoll += st.session_state.final_diagnose + "\n"

    if "therapie_vorschlag" in st.session_state:
        protokoll += "\n---\n Therapiekonzept:\n"
        protokoll += st.session_state.therapie_vorschlag + "\n"

    protokoll += "\n---\n Strukturierte Rückmeldung:\n"
    protokoll += st.session_state.final_feedback + "\n"

    st.download_button(
        label="⬇️ Gespräch & Feedback herunterladen",
        data=protokoll,
        file_name="karina_chatprotokoll.txt",
        mime="text/plain"
    )
else:
    st.info("💬 Der Download wird nach Abschluss der Evaluation freigeschaltet.")
