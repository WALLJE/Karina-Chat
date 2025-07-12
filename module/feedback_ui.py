import streamlit as st
from datetime import datetime
from supabase import create_client, Client

# Supabase initialisieren (Erwartung: in st.secrets definiert)
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]
supabase: Client = create_client(supabase_url, supabase_key)

def student_feedback():
    st.markdown("---")
    st.subheader("🗣 Ihr Feedback zur Simulation")
    jetzt = datetime.now()
    start = st.session_state.get("startzeit", jetzt)
    bearbeitungsdauer = (jetzt - start).total_seconds() / 60  # in Minuten

   
    st.markdown("Bitte bewerten Sie die folgenden Aspekte auf einer Schulnoten-Skala von 1 (sehr gut) bis 6 (ungenügend):")

    f1 = st.radio("1. Wie realistisch war das Fallbeispiel?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f1 in [5, 6]:
        st.info("❗Vielen Dank für die kritische Rückmeldung. Erklären Sie gern Ihre Bewertung im Freitext unten konkreter.")

    f2 = st.radio("2. Wie hilfreich war die Simulation für das Training der Anamnese?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f2 in [5, 6]:
        st.info("❗Was hätten Sie sich beim Anamnese-Training anders gewünscht? Bitte erläutern Sie unten, damit wir Ihr Feedback besser verstehen und die App anpassen können.")

    f3 = st.radio("3. Wie verständlich und relevant war das automatische Feedback?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f3 in [5, 6]:
        st.info("❗Sie sind mit dem Feedback unzufrieden. Wir möchten gern besser werden. Beschreiben Sie deswegen bitte im folgenden Freitext warum.")

    f4 = st.radio("4. Wie bewerten Sie den didaktischen Gesamtwert der Simulation?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f4 in [5, 6]:
        st.info("❗Was hat aus Ihrer Sicht den didaktischen Wert eingeschränkt? Bitte erläutern Sie uns Ihre Kritik.")

    f5 = st.radio("5. Wie schwierig fanden Sie den Fall? *1 = sehr einfach, 6 = sehr schwer*", [1, 2, 3, 4, 5, 6], horizontal=True)

    f7 = st.selectbox(
        "In welchem Semester befinden Sie sich aktuell?",
        ["", "Vorklinik", "5. Semester", "6. Semester", "7. Semester", "8. Semester", "9. Semester", "10. Semester oder höher", "Praktisches Jahr"]
    )

    bugs = st.text_area("💬 Welche Ungenauigkeiten oder Fehler sind Ihnen aufgefallen (optional):", "")
    kommentar = st.text_area("💬 Freitext (optional):", "")
    abgeschickt = st.form_submit_button("📩 Feedback absenden")

    if abgeschickt:
        verlauf = "\n".join([
            f"👨 Du: {m['content']}" if m['role'] == 'user' else f"👩 Patientin: {m['content']}"
            for m in st.session_state.get("messages", [])[1:]  # ohne system-prompt
        ])

        befunde = st.session_state.get("befunde", "")

        weitere_befunde = ""
        gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
        for i in range(2, gesamt + 1):
            bef_key = f"befunde_runde_{i}"
            inhalt = st.session_state.get(bef_key, "")
            if inhalt:
                weitere_befunde += f"\n\n📅 Termin {i}:{inhalt}"

        eintrag = {
            "datum": jetzt.strftime("%Y-%m-%d"),
            "uhrzeit": jetzt.strftime("%H:%M:%S"),
            "bearbeitungsdauer_min": round(bearbeitungsdauer, 1),
            "szenario": st.session_state.get("diagnose_szenario", ""),
            "patient_name": st.session_state.get("patient_name", ""),
            "patient_age": st.session_state.get("patient_age", ""),
            "patient_job": st.session_state.get("patient_job", ""),
            "patient_verhalten": st.session_state.get("patient_verhalten_memo", "unbekannt"),
            "note_realismus": f1,
            "note_anamnese": f2,
            "note_feedback": f3,
            "note_didaktik": f4,
            "fall_schwere": f5,
            "semester": f7,
            "fall_bug": bugs,
            "kommentar": kommentar,
            "chatverlauf": verlauf,
            "verdachtsdiagnosen": st.session_state.get("user_ddx2", "nicht angegeben"),
            "befunde": befunde + weitere_befunde,
            "finale_diagnose": st.session_state.get("final_diagnose", "nicht angegeben"),
            "therapie": st.session_state.get("therapie_vorschlag", "nicht angegeben"),
            "gpt_feedback": st.session_state.get("final_feedback", "Kein KI-Feedback erzeugt")
        }

        try:
            supabase.table("feedback_studi").insert(eintrag).execute()
            st.success("✅ Vielen Dank, Ihr Feedback wurde gespeichert.")
        except Exception as e:
            st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")

