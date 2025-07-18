import streamlit as st
from datetime import datetime
import json

def speichere_gpt_feedback_in_supabase():
    jetzt = datetime.now()
    start = st.session_state.get("startzeit", jetzt)
    dauer_min = round((jetzt - start).total_seconds() / 60, 1)

    # Chatverlauf ohne system-prompt
    verlauf = "\n".join([
        f"👨 Du: {m['content']}" if m['role'] == 'user' else f"👩 Patientin: {m['content']}"
        for m in st.session_state.get("messages", [])[1:]
    ])

    # Befunde aus erster Runde
    befunde = st.session_state.get("befunde", "")

    # Weitere Befunde
    weitere_befunde = ""
    gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
    for i in range(2, gesamt + 1):
        bef_key = f"befunde_runde_{i}"
        inhalt = st.session_state.get(bef_key, "")
        if inhalt:
            weitere_befunde += f"\n\n📅 Termin {i}:{inhalt}"

    alle_befunde = befunde + weitere_befunde

    gpt_row = {
        "datum": jetzt.strftime("%Y-%m-%d"),
        "uhrzeit": jetzt.strftime("%H:%M:%S"),
        "bearbeitungsdauer_min": dauer_min,
        "szenario": st.session_state.get("diagnose_szenario", ""),
        "name": st.session_state.get("patient_name", ""),
        "alter": st.session_state.get("patient_age", ""),
        "beruf": st.session_state.get("patient_job", ""),
        "verhalten": st.session_state.get("patient_verhalten_memo", "unbekannt"),
        "verdachtsdiagnosen": st.session_state.get("user_ddx2", ""),
        "diagnostik": st.session_state.get("diagnostik_eingaben_kumuliert", ""),
        "finale_diagnose": st.session_state.get("final_diagnose", ""),
        "therapie": st.session_state.get("therapie_vorschlag", ""),
        "gpt_feedback": st.session_state.get("final_feedback", ""),
        "chatverlauf": verlauf,
        "befunde": alle_befunde
    }

    try:
        from supabase import create_client
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        gpt_row_serialisiert = json.loads(json.dumps(gpt_row, default=str))
        supabase.table("feedback_gpt").insert(gpt_row_serialisiert).execute()
        # DEBUG 
        # st.success("✅ GPT-Feedback wurde gespeichert.")
    except Exception as e:
        st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")
