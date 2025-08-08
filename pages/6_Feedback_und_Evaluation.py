import streamlit as st
from datetime import datetime
from sprachmodul import sprach_check
from feedbackmodul import feedback_erzeugen
from supabase import create_client, Client
from module.feedback_ui import student_feedback
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.gpt_feedback import speichere_gpt_feedback_in_supabase
from diagnostikmodul import aktualisiere_diagnostik_zusammenfassung

show_sidebar()
copyright_footer()

client = st.session_state["openai_client"]

# Voraussetzungen prüfen
if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
    st.warning("⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite.")
    st.page_link("Karina_Chat_2.py", label="⬅ Zur Startseite")
    st.stop()

#if not st.session_state.get("final_diagnose") or not st.session_state.get("therapie_vorschlag"):
#    st.warning("⚠️ Bitte zuerst Diagnose und Therapie eingeben.")
#    st.stop()

aktualisiere_diagnostik_zusammenfassung()

# feedback

if st.session_state.get("final_feedback", "").strip():
    st.markdown(st.session_state.final_feedback)
    
        # NEU: Nur wenn noch nicht gespeichert
        if "feedback_row_id" not in st.session_state:
            from module.gpt_feedback import speichere_gpt_feedback_in_supabase
            speichere_gpt_feedback_in_supabase()
else:
    if st.button("📋 Abschluss-Feedback anzeigen"):
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

        feedback = feedback_erzeugen(
            st.session_state["openai_client"],  # falls als client gespeichert
            final_diagnose,
            therapie_vorschlag,
            user_ddx2,
            diagnostik_eingaben,
            gpt_befunde,
            koerper_befund,
            user_verlauf,
            anzahl_termine,
            diagnose_szenario
        )
        st.session_state.final_feedback = feedback
        speichere_gpt_feedback_in_supabase()
        st.success("✅ Evaluation erstellt")
        st.rerun()



# Downloadbereich
# Zusammenfassung und Download vorbereiten
st.markdown("---")
st.subheader("📄 Download")

if "final_feedback" in st.session_state:
    protokoll = ""

    # Szenario
    protokoll += f"Simuliertes Krankheitsbild: {st.session_state.diagnose_szenario}\n\n"

    # Gesprächsverlauf
    protokoll += "---\n💬 Gesprächsverlauf (nur Fragen des Studierenden):\n"
    for msg in st.session_state.messages[1:]:
        rolle = st.session_state.patient_name if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n"

    # Körperlicher Untersuchungsbefund
    if "koerper_befund" in st.session_state:
        protokoll += "\n---\n Körperlicher Untersuchungsbefund:\n"
        protokoll += st.session_state.koerper_befund + "\n"

    # Differentialdiagnosen
    if "user_ddx2" in st.session_state:
        protokoll += "\n---\n Erhobene Differentialdiagnosen:\n"
        protokoll += st.session_state.user_ddx2 + "\n"

    # Diagnostische Maßnahmen
    if "diagnostik_eingaben_kumuliert" in st.session_state:
        protokoll += "\n---\n Geplante diagnostische Maßnahmen (alle Termine):\n"
        protokoll += st.session_state.diagnostik_eingaben_kumuliert + "\n"
    
    # KUmulierte Befunde
    if "gpt_befunde_kumuliert" in st.session_state:
        protokoll += "\n---\n📄 Ergebnisse der diagnostischen Maßnahmen:\n"
        protokoll += st.session_state.gpt_befunde_kumuliert + "\n"


    # Finale Diagnose
    if "final_diagnose" in st.session_state:
        protokoll += "\n---\n Finale Diagnose:\n"
        protokoll += st.session_state.final_diagnose + "\n"

    # Therapiekonzept
    if "therapie_vorschlag" in st.session_state:
        protokoll += "\n---\n Therapiekonzept:\n"
        protokoll += st.session_state.therapie_vorschlag + "\n"

    # Abschlussfeedback
    protokoll += "\n---\n Strukturierte Rückmeldung:\n"
    protokoll += st.session_state.final_feedback + "\n"

    # Download-Button
    st.download_button(
        label="⬇️ Gespräch & Feedback herunterladen",
        data=protokoll,
        file_name="karina_chatprotokoll.txt",
        mime="text/plain"
    )
else:
    st.info("💬 Das Protokoll kann nach der Evaluation heruntergeladen werden.")

# Abschnitt: Evaluation durch Studierende mit Schulnoten und Sammeldatei

if st.session_state.final_feedback:
    student_feedback()
