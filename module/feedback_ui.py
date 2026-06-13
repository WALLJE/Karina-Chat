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

    # Likert-Skala zentral definieren
    likert_options = [
        "Trifft voll zu", 
        "Trifft eher zu", 
        "Teils/teils", 
        "Trifft eher nicht zu", 
        "Trifft gar nicht zu"
    ]
    
    negativ_antworten = ["Trifft eher nicht zu", "Trifft gar nicht zu"]

    # ---------------------------------------------------------
    # GRUPPE 1: Simulation & Fall (OHNE Überschrift)
    # ---------------------------------------------------------
    st.markdown("Bitte bewerten Sie die folgenden Aspekte zur Simulation:")

    f_bedienung = st.radio("Die Bedienung der Simulation ist intuitiv und unkompliziert.", likert_options, horizontal=True)
    
    f1 = st.radio("Das Fallbeispiel wirkte auf mich realistisch.", likert_options, horizontal=True)
    if f1 in negativ_antworten:
        st.info("❗Vielen Dank für die kritische Rückmeldung: Erklären Sie gern unten im Freitext konkreter, was nicht realistisch wirkte.")

    f2 = st.radio("Die Simulation ist hilfreich für das Training der Anamnese.", likert_options, horizontal=True)
    if f2 in negativ_antworten:
        st.info("❗Was hätten Sie sich beim Anamnese-Training anders gewünscht? Bitte erläutern Sie unten, damit wir die App anpassen können.")

    f3 = st.radio("Das KI-generierte Feedback war verständlich und relevant.", likert_options, horizontal=True)
    if f3 in negativ_antworten:
        st.info("❗Sie sind mit dem Feedback unzufrieden. Wir möchten gern besser werden. Beschreiben Sie bitte im folgenden Freitext warum.")

    f4 = st.radio("Die Simulation stellt insgesamt ein wertvolles Lernangebot dar.", likert_options, horizontal=True)
    if f4 in negativ_antworten:
        st.info("❗Was hat aus Ihrer Sicht den didaktischen Wert eingeschränkt? Bitte erläutern Sie uns Ihre Kritik.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Bewertung der Fallschwere:**")
    st.markdown("(-2 = deutlich zu leicht, 0 = passend, +2 = deutlich zu schwer)")
    
    f5 = st.radio(
        "Verstecktes Label für Fallschwere",
        [-2, -1, 0, 1, 2],
        index=2,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    fallschwere_begruendung = ""
    if f5 <= -1:
        fallschwere_begruendung = st.text_area("Ihre Vorschläge für mehr Anspruch:", key="schwere_leicht")
    elif f5 >= 1:
        fallschwere_begruendung = st.text_area("Ihre Vorschläge zur Erleichterung:", key="schwere_schwer")

    st.markdown("---")

    # ---------------------------------------------------------
    # GRUPPE 2: Safe Space & Psychological Safety
    # ---------------------------------------------------------
    eval_safespace_umgebung = st.radio(
        "Die Simulation bietet eine geschützte Lernumgebung.", 
        likert_options, horizontal=True
    )
    eval_safespace_entscheidung = st.radio(
        "Ich kann in der Simulation das Treffen von klinischen Entscheidungen üben.", 
        likert_options, horizontal=True
    )
    eval_safespace_stress = st.radio(
        "Das unbeobachtete Üben führte bei mir zu einem deutlich reduzierten Stressempfinden während der Anamnese.", 
        likert_options, horizontal=True
    )
    eval_safespace_fehler = st.radio(
        "In der KI-Simulation fiel es mir leichter als im klassischen Kommunikationstraining (z. B. mit Schauspielpatienten), Fehler zuzulassen und daraus zu lernen.", 
        likert_options, horizontal=True
    )
    eval_safespace_exploration = st.radio(
        "Ich habe bewusst klinische Entscheidungen ausprobiert, bei denen ich mir im realen Setting unsicher gewesen wäre.", 
        likert_options, horizontal=True
    )
    eval_konsistenz = st.radio(
        "Die Antworten der simulierten Patientin waren konsistent und medizinisch plausibel.", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # GRUPPE 3: Clinical Reasoning
    # ---------------------------------------------------------
    eval_reasoning_1 = st.radio(
        "Das Training mit der App fördert mein strukturiertes klinisches Denken.", 
        likert_options, horizontal=True
    )
    eval_reasoning_2 = st.radio(
        "Durch die Simulation fühle ich mich besser auf zukünftige, reale Patientenkontakte vorbereitet.", 
        likert_options, horizontal=True
    )
    eval_feedback_1 = st.radio(
        "Das Feedback der KI war fachlich nachvollziehbar.", 
        likert_options, horizontal=True
    )
    eval_feedback_2 = st.radio(
        "Das Feedback der KI hat mir geholfen, Stärken und Verbesserungsmöglichkeiten in meinem Vorgehen zu erkennen.", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # GRUPPE 4: Didaktische Integration
    # ---------------------------------------------------------
    eval_integration = st.radio(
        "Ich empfinde die KI-Simulation als eine sinnvolle Ergänzung zum klassischen Unterricht.", 
        likert_options, horizontal=True
    )
    eval_anforderungen = st.radio(
        "Die Anforderungen der Simulation passten zu meinem bisherigen Ausbildungsstand.", 
        likert_options, horizontal=True
    )
    eval_weitere_faelle = st.radio(
        "Ich würde die Simulation auch zur Bearbeitung weiterer Fälle nutzen.", 
        likert_options, horizontal=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # GRUPPE 5: Technik & Allgemeine Angaben
    # ---------------------------------------------------------
    tech_probleme = st.radio(
        "Technische Probleme haben meinen Lernprozess beeinträchtigt.",
        ["Ja", "Nein"], 
        index=1,  
        horizontal=True
    )
    
    tech_probleme_begruendung = ""
    if tech_probleme == "Ja":
        tech_probleme_begruendung = st.text_area("Welche technischen Probleme traten konkret auf?", key="tech_bug_text")

    ki_vorerfahrung = st.radio(
        "Ich nutze KI-Tools (z. B. ChatGPT) bereits regelmäßig für mein Studium oder privat.", 
        likert_options, horizontal=True
    )
    
    f7 = st.selectbox(
        "In welchem Semester befinden Sie sich aktuell?",
        ["", "Vorklinik", "5. Semester", "6. Semester", "7. Semester", "8. Semester", "9. Semester", "10. Semester oder höher", "Praktisches Jahr"]
    )

    matrikelnummer = st.text_input(
        "Matrikelnummer (optional)",
        value="",
        help="Die Matrikelnummer wird verschlüsselt gespeichert und ist nur erforderlich, wenn die Simulation als Lehrveranstaltungsaufgabe bearbeitet wurde."
    )

    bugs = st.text_area("💬 Welche sonstigen Ungenauigkeiten oder Fehler sind Ihnen aufgefallen (optional):", "")
    kommentar = st.text_area("💬 Freitext (optional):", "")

    if st.button("📩 Feedback absenden", disabled=offline_active):
        if offline_active:
            st.info("🔌 Offline-Modus: Feedback konnte nicht gespeichert werden.")
            return

        eintrag = {
            "note_bedienung": f_bedienung,
            "note_realismus": f1,
            "note_anamnese": f2,
            "note_feedback": f3,
            "note_didaktik": f4,
            "fall_schwere": f5,
            "fallschwere_begruendung": fallschwere_begruendung,
            "eval_safespace_umgebung": eval_safespace_umgebung,
            "eval_safespace_entscheidung": eval_safespace_entscheidung,
            "eval_safespace_stress": eval_safespace_stress,
            "eval_safespace_fehler": eval_safespace_fehler,
            "eval_safespace_exploration": eval_safespace_exploration,
            "eval_konsistenz": eval_konsistenz,
            "eval_reasoning_denken": eval_reasoning_1,
            "eval_reasoning_vorbereitung": eval_reasoning_2,
            "eval_feedback_fachlich": eval_feedback_1,
            "eval_feedback_lerneffekt": eval_feedback_2,
            "eval_integration": eval_integration,
            "eval_anforderungen_passen": eval_anforderungen,
            "eval_weitere_faelle": eval_weitere_faelle,
            "tech_probleme": tech_probleme,
            "tech_probleme_begruendung": tech_probleme_begruendung,
            "ki_vorerfahrung": ki_vorerfahrung,
            "semester": f7,
            "fall_bug": bugs,
            "kommentar": kommentar,
            "Matrikel": _encrypt_matrikel(matrikelnummer.strip())
        }

        try:
            row_id = st.session_state.get("feedback_row_id")
            
            if row_id is not None:
                supabase.table("feedback_gpt").update(eintrag).eq("ID", row_id).execute()
                
                limesurvey_id = st.session_state.get("limesurvey_id")
                if limesurvey_id:
                    try:
                        gewinnspiel_eintrag = {
                            "limesurvey_id": limesurvey_id
                        }
                        supabase.table("gewinnspiel_teilnehmer").insert(gewinnspiel_eintrag).execute()
                    except Exception as err:
                        st.error(f"⚠️ Das Feedback wurde gespeichert, aber bei der Gewinnspiel-Registrierung gab es ein Problem: {repr(err)}")

                st.success("✅ Vielen Dank! Ihr Feedback wurde sicher und anonym gespeichert.")
                st.session_state["student_evaluation_done"] = True
                st.rerun()
            else:
                st.warning("ℹ️ Konnte den ursprünglichen Datensatz nicht zuordnen (ID fehlt). Bitte Fall neu starten oder Admin informieren.")
        except Exception as e:
            st.error(f"🚫 Fehler beim Speichern in Supabase: {repr(e)}")
