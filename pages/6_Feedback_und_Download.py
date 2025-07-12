import streamlit as st
from datetime import datetime
from sprachmodul import sprach_check
from feedbackmodul import feedback_erzeugen
from supabase import create_client, Client

if not st.session_state.get("final_diagnose") or not st.session_state.get("therapie_vorschlag"):
    st.warning("⚠️ Bitte zuerst Diagnose und Therapie eingeben.")
    st.stop()


# feedback

if st.session_state.get("final_feedback", "").strip():
    st.markdown(st.session_state.final_feedback)
else:
    if st.button("📋 Abschluss-Feedback anzeigen"):
        diagnostik_eingaben = st.session_state.get("diagnostik_eingaben", "")
        gpt_befunde = st.session_state.get("gpt_befunde", "")
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
        st.success("✅ Evaluation erstellt")
        st.rerun()
