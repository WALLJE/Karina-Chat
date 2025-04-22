import streamlit as st
from openai import OpenAI
import os

# ✅ OpenAI-Client mit API-Key starten
# Hinweis: In Streamlit Cloud kannst du den Key in "Secrets" speichern
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY"))

# 🧠 System-Prompt: definiert Karinas Verhalten
SYSTEM_PROMPT = """
Patientensimulation (Morbus Crohn)

Rolle der virtuellen Patientin:

    Du bist Karina, eine 24-jährige Studentin der Wirtschaftswissenschaften.
    Dein Gesprächspartner ist ein Medizinstudent, der als Arzt handelt.
    Du kommunizierst in normaler Umgangssprache mit einem höflichen und besorgten Ton, vermeidest jedoch Fachjargon.
    Wenn du medizinische Begriffe nicht verstehst, fragst du nach, ohne dich dafür zu entschuldigen.
    Du bist ungeduldig, wenn längere Pausen entstehen, und fragst nach dem weiteren Vorgehen.

Sprich zu Beginn eher knapp. Beantworte Fragen grundsätzlich nur so ausführlich, wie direkt danach gefragt wurde. 
Nenne Symptome wie Fieber, Nachtschweiß oder Gewichtsverlust erst, wenn direkt danach gefragt wird.

Krankengeschichte (Symptome & Hintergrund):

    Beschwerden: Seit 4 Monaten hast du Bauchschmerzen, hauptsächlich im rechten Unterbauch.
    Die Schmerzen treten wiederkehrend auf, gelegentlich begleitet von Fieber bis 38,5 °C und Nachtschweiß.
    Stuhlgang: Breiig, 5-mal täglich.
    Gewichtsverlust: 5 kg in der letzten Woche ohne Diät.
    Familiengeschichte: Keine bekannten Darmerkrankungen.
    Reisen: Vor 5 Jahren Korsika, sonst nur in Deutschland.

Untersuchungsbefunde (auf Nachfrage):

    „Das können wir hier nicht simulieren. Ich habe normale Darmgeräusche, aber deutlichen Druckschmerz und eine Resistenz im rechten Unterbauch. Sonst ist alles unauffällig.“

Diagnostik:

    Lehne Diagnostik ab, bis die gesamte Anamnese erfragt wurde.
    CT strikt ablehnen wegen Strahlenangst.
    MRT wäre in Ordnung, erwähne es aber nicht von selbst.

Koloskopie:

    Fordere eine ärztliche Aufklärung zur Koloskopie.
    Frage kritisch nach Vorbereitung, Sedierung, Risiken, Verhalten danach, Alternativen.

Therapie:

    Zeige Besorgnis bei Prednisolon/Cortison.
    Frage gezielt nach Nebenwirkungen (mind. 4), Alternativen, Erfolgsaussichten.
    Frage auch nach chirurgischen Optionen.

Abschluss:

    Bedanke dich für die Betreuung.
    Frage: „Möchtest du ein Feedback zum Anamnesegespräch?“
"""

# 🧱 Streamlit-UI: Titel anzeigen
st.title("🩺 Patientensimulation: Gespräch mit Karina")

# 💬 Session-State initialisieren: Nachrichtenverlauf starten
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Guten Tag, ich bin froh, dass ich mich heute bei Ihnen vorstellen kann."}
    ]

# 📜 Chatverlauf anzeigen (ohne Systemnachricht)
for msg in st.session_state.messages[1:]:
    sender = "👩 Karina" if msg["role"] == "assistant" else "🧑 Du"
    st.markdown(f"**{sender}:** {msg['content']}")

# 📥 Eingabemaske mit Formular & Button (verhindert Endlosschleife)
with st.form(key="eingabe_formular", clear_on_submit=True):
    user_input = st.text_input("Deine Frage an Karina:")
    submit_button = st.form_submit_button(label="Absenden")

# 🤖 GPT-4 ansprechen, wenn Button gedrückt wurde
if submit_button and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Karina antwortet..."):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state.messages,
            temperature=0.6
        )
        reply = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": reply})

    st.rerun()  # UI neu laden, damit neue Nachricht angezeigt wird

# --------------------------------------------
# 🧠 FEEDBACK-FUNKTION FÜR STUDIERENDE
# --------------------------------------------

st.markdown("---")
st.subheader("🧠 Feedback & Evaluation")

# Toggle-Schalter für das Feedback-Formular
if "show_feedback_form" not in st.session_state:
    st.session_state.show_feedback_form = False

if st.button("Feedback & Evaluation starten"):
    st.session_state.show_feedback_form = True

# Feedback-Formular anzeigen
if st.session_state.show_feedback_form:
    ddx_input = st.text_area("Welche drei Differentialdiagnosen halten Sie für möglich?", key="ddx_input")
    diag_input = st.text_area("Welche diagnostischen Maßnahmen halten Sie für sinnvoll?", key="diag_input")

    if st.button("Feedback anzeigen"):
        # Nur Patientenantworten extrahieren
        patient_text = "\n".join([
            msg["content"] for msg in st.session_state.messages
            if msg["role"] == "assistant"
        ])

        # GPT-Prompt zur Bewertung
        feedback_prompt = f"""
Du bist ein erfahrener medizinischer Prüfer. Ein Medizinstudent hat mit einer Patientin gesprochen. 

Differentialdiagnosen:
{ddx_input}

Vorgeschlagene Diagnostik:
{diag_input}

Hier ist der Chatverlauf der Patientin:
{patient_text}

Bitte gib ein medizinisch-wissenschaftlich fundiertes, konstruktiv-kritisches Feedback:
- Wurden alle relevanten anamnestischen Informationen für diese Diagnosen erfragt?
- Sind die vorgeschlagenen diagnostischen Maßnahmen sinnvoll und vollständig?
- Fehlt etwas Wichtiges?

Strukturiere dein Feedback klar und verständlich.
"""

        with st.spinner("Bewertung wird erstellt..."):
            feedback_response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": feedback_prompt}],
                temperature=0.4
            )
            feedback = feedback_response.choices[0].message.content

        st.session_state.generated_feedback = feedback

        st.success("✅ Feedback erstellt")
        st.markdown("### 📋 Automatisiertes Feedback:")
        st.markdown(feedback)

# --------------------------------------------
# 📄 DOWNLOADBEREICH (Chat + Feedback als Textdatei)
# --------------------------------------------

st.markdown("---")
st.subheader("📝 Download des Chatprotokolls")

if "generated_feedback" in st.session_state:
    protokoll = ""

    # Nachrichtenverlauf formatieren
    for msg in st.session_state.messages[1:]:
        rolle = "Karina" if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n\n"

    # Feedback hinzufügen
    protokoll += "\n---\n📋 Automatisiertes Feedback:\n"
    protokoll += st.session_state.generated_feedback

    st.download_button(
        label="⬇️ Gespräch & Feedback als Textdatei herunterladen",
        data=protokoll,
        file_name="karina_chatprotokoll.txt",
        mime="text/plain"
    )
else:
    st.info("💬 Das Protokoll kann nach dem Feedback heruntergeladen werden.")
