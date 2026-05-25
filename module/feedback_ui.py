import streamlit as st
from datetime import datetime
from supabase import create_client, Client
from cryptography.fernet import Fernet, InvalidToken
from module.offline import is_offline

# Supabase initialisieren
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]
supabase: Client = create_client(supabase_url, supabase_key)


def _encrypt_matrikel(matrikel: str) -> str | None:
    if not matrikel:
        return None

    try:
        key = st.secrets["supabase"]["matrikel_key"]
    except KeyError:
        st.warning(
            "ℹ️ Hinweis: Die Matrikelnummer konnte nicht verschlüsselt werden, da kein Schlüssel hinterlegt ist."
        )
        return None

    try:
        fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        token = fernet.encrypt(matrikel.encode("utf-8"))
        return token.decode("utf-8")
    except (InvalidToken, ValueError) as err:
        st.error(f"🚫 Fehler bei der Verschlüsselung der Matrikelnummer: {err}")
    except Exception as err:
        st.error(f"🚫 Unerwarteter Fehler bei der Verschlüsselung: {repr(err)}")

    return None


def student_feedback():
    st.markdown("---")
    st.subheader("🗣 Ihr Feedback zur Simulation")

    offline_active = is_offline()
    if offline_active:
        st.info(
            "🔌 Offline-Modus aktiv: Ihr Feedback wird derzeit nicht an Supabase übermittelt."
        )

    if st.session_state.get("student_evaluation_done"):
        st.success("✅ Vielen Dank! Ihr Feedback wurde bereits gespeichert.")
        return

    jetzt = datetime.now()
    start = st.session_state.get("startzeit", jetzt)

    # ---------------------------------------------------------
    # BLOCK 1: Fall & Simulation
    # ---------------------------------------------------------
    st.markdown("#### 1. Fall & Simulation")
    st.markdown("Bitte bewerten Sie die folgenden Aspekte auf einer Schulnoten-Skala von 1 (sehr gut) bis 6 (ungenügend):")

    f1 = st.radio("Wie realistisch war das Fallbeispiel?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f1 >= 4:
        st.info("❗Vielen Dank für die kritische Rückmeldung: Sie halten das Fallbeispiel nicht für realistisch. Erklären Sie gern Ihre Bewertung im Freitext unten konkreter.")

    f2 = st.radio("Wie hilfreich war die Simulation für das Training der Anamnese?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f2 >= 4:
        st.info("❗Sie scheinen die Simuation nicht für hilfreich zu erachten. Was hätten Sie sich beim Anamnese-Training anders gewünscht? Bitte erläutern Sie unten, damit wir Ihr Feedback besser verstehen und die App anpassen können.")

    f3 = st.radio("Wie verständlich und relevant war das automatische Feedback?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f3 >= 4:
        st.info("❗Sie sind mit dem Feedback unzufrieden. Wir möchten gern besser werden. Beschreiben Sie deswegen bitte im folgenden Freitext warum.")

    f4 = st.radio("Wie bewerten Sie den didaktischen Gesamtwert der Simulation?", [1, 2, 3, 4, 5, 6], horizontal=True)
    if f4 >= 4:
        st.info("❗Was hat aus Ihrer Sicht den didaktischen Wert eingeschränkt? Bitte erläutern Sie uns Ihre Kritik.")

    st.markdown("**Fallschwere-Skala:** -2 = deutlich zu leicht, 0 = passend, +2 = deutlich zu schwer.")
    f5 = st.radio(
        "Wie schwierig fanden Sie den Fall?",
        [-2, -1, 0, 1, 2],
        index=2,  # <-- Das setzt den Standardwert auf 0 
        horizontal=True,
    )
    
    # Variable für die Begründung initialisieren
    fallschwere_begruendung = ""
    
    if f5 == -2:
        st.info("❗Der Fall war für Sie deutlich zu leicht. Was würden Sie verbessern, damit die Aufgabe anspruchsvoller wird?")
        fallschwere_begruendung = st.text_area("Ihre Vorschläge für mehr Anspruch:", key="schwere_leicht")
    elif f5 == 2:
        st.info("❗Der Fall war für Sie deutlich zu schwer. Was würden Sie verbessern, damit die Aufgabe fairer und verständlicher wird?")
        fallschwere_begruendung = st.text_area("Ihre Vorschläge zur Erleichterung:", key="schwere_schwer")

    st.markdown("---")

    # Definition der Antwortmöglichkeiten für die neuen Blöcke
    likert_options = [
        "Trifft voll zu", 
        "Trifft eher zu", 
        "Teils/teils", 
        "Trifft eher nicht zu", 
        "Trifft gar nicht zu"
    ]

    # ---------------------------------------------------------
    # BLOCK 2: Safe Space & Lernatmosphäre
    # ---------------------------------------------------------
    st.markdown("#### 2. Safe Space")
    eval_safespace = st.radio(
        "Die Simulation bietet mir einen Safe Space, in dem ich ohne Druck klinische Entscheidungen treffen kann.", 
        likert_options, horizontal=True
    )
    eval_angst = st.radio(
        "Das automatische Feedback nimmt mir die Angst davor, im klinischen Alltag Fehler zu machen.", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # BLOCK 3: Clinical Reasoning & Lerneffekt
    # ---------------------------------------------------------
    st.markdown("#### 3. Clinical Reasoning")
    eval_reasoning = st.radio(
        "Das Training mit der App fördert mein strukturiertes klinisches Denken.", 
        likert_options, horizontal=True
    )
    eval_sicherheit = st.radio(
        "Durch die Simulation fühle ich mich sicherer für zukünftige, reale Patientenkontakte.", 
        likert_options, horizontal=True
    )
    eval_feedback_praezise = st.radio(
        "Das Feedback der KI war fachlich präzise und hat mir geholfen, meine Fehler zu verstehen.", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # BLOCK 4: Didaktische Integration
    # ---------------------------------------------------------
    st.markdown("#### 4. Didaktische Integration")
    eval_integration = st.radio(
        "Ich empfinde die KI-Simulation als eine sinnvolle Ergänzung zum klassischen Unterricht (z. B. Skills-Lab).", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # BLOCK 5: Allgemeine Angaben & Kommentare
    # ---------------------------------------------------------
    st.markdown("#### 5. Allgemeine Angaben & Kommentare")
    
    f7 = st.selectbox(
        "In welchem Semester befinden Sie sich aktuell?",
        ["", "Vorklinik", "5. Semester", "6. Semester", "7. Semester", "8. Semester", "9. Semester", "10. Semester oder höher", "Praktisches Jahr"]
    )

    matrikelnummer = st.text_input(
        "Matrikelnummer (optional)",
        value="",
        help="Die Matrikelnummer wird verschlüsselt gespeichert und ist nur erforderlich, wenn die Simulation als Lehrveranstaltungsaufgabe bearbeitet wurde."
    )

    bugs = st.text_area("💬 Welche Ungenauigkeiten oder Fehler sind Ihnen aufgefallen (optional):", "")
    kommentar = st.text_area("💬 Freitext (optional):", "")

    if st.button("📩 Feedback absenden", disabled=offline_active):
        if offline_active:
            st.info("🔌 Offline-Modus: Feedback konnte nicht gespeichert werden.")
            return

        # Hier werden alle alten UND neuen Werte in das Dictionary gepackt
        eintrag = {
            "note_realismus": f1,
            "note_anamnese": f2,
            "note_feedback": f3,
            "note_didaktik": f4,
            "fall_schwere": f5,
            "fallschwere_begruendung": fallschwere_begruendung,  # NEU HINZUGEFÜGT
            "eval_safespace": eval_safespace,
            "eval_angst": eval_angst,
            "eval_reasoning": eval_reasoning,
            "eval_sicherheit": eval_sicherheit,
            "eval_feedback_praezise": eval_feedback_praezise,
            "eval_integration": eval_integration,
            "semester": f7,
            "fall_bug": bugs,
            "kommentar": kommentar,
            "Matrikel": _encrypt_matrikel(matrikelnummer.strip())
        }

        try:
            row_id = st.session_state.get("feedback_row_id")
            
            if row_id is not None:
                supabase.table("feedback_gpt").update(eintrag).eq("ID", row_id).execute()
                st.success("✅ Vielen Dank! Ihr Feedback wurde gespeichert.")
                st.session_state["student_evaluation_done"] = True
                st.rerun()
            else:
                st.warning("ℹ️ Konnte den ursprünglichen Datensatz nicht zuordnen (ID fehlt). Bitte Fall neu starten oder Admin informieren.")
        except Exception as e:
            st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")
