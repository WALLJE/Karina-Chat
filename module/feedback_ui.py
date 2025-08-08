import streamlit as st
from datetime import datetime
from supabase import create_client, Client
import json

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

    if st.button("📩 Feedback absenden"):

    
        
        eintrag = {
            "note_realismus": f1,
            "note_anamnese": f2,
            "note_feedback": f3,
            "note_didaktik": f4,
            "fall_schwere": f5,
            "semester": f7,
            "fall_bug": bugs,
            "kommentar": kommentar
        }

    try:
        row_id = st.session_state.get("feedback_row_id")
        if row_id is None:
            # Fallback: versuche den zuletzt angelegten Datensatz zu finden (optional)
            # Achtung: nur verwenden, wenn das für dich logisch ist:
            # last = supabase.table("feedback_gpt").select("ID").order("ID", desc=True).limit(1).single().execute()
            # row_id = last.data["ID"] if last and last.data else None
            pass

        if row_id is not None:
            supabase.table("feedback_gpt").update(eintrag).eq("ID", row_id).execute()
            st.success("✅ Vielen Dank! Ihr Feedback wurde gespeichert.")
        else:
            st.warning("ℹ️ Konnte den ursprünglichen Datensatz nicht zuordnen (ID fehlt). Bitte Fall neu starten oder Admin informieren.")
    except Exception as e:
        st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")
