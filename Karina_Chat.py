import streamlit as st
from openai import OpenAI
import os

# API-Key setzen
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#System-Prompt
SYSTEM_PROMPT = """
Patientensimulation (Morbus Crohn)
[...gekürzt für Klarheit...]
"""

# Titel und Instruktion
st.title("Patientensimulation: Gespräch mit Karina")
st.info("""
**Instruktionen für Studierende:**

Sie führen ein strukturiertes Anamnesegespräch mit der virtuellen Patientin Karina.
Geben Sie zum Beginn Ihre Fragen an die Patientin unten ein. Ziel ist es, durch gezieltes Nachfragen eine Verdachtsdiagnose zu stellen und sinnvolle weitere Diagnostik zu planen.

Bitte beachten Sie:
- Karina antwortet nur auf das, was direkt gefragt wird.
- Medizinische Fachsprache versteht sie nicht unbedingt – erklären Sie unklare Begriffe.
- Nach längeren Gesprächspausen wird Karina ungeduldig oder besorgt.

Wenn Sie genug anemnestische Informationen erhoben haben:
- Führen Sie eine körperliche Untersuchung durch (per Button unten).
- Danach: Nennen Sie Ihre Differentialdiagnosen und die gewünschte Diagnostik.
- Sie erhalten typische Befunde und sollen dann eine Diagnose und Therapie festlegen.
- Danach folgt ein strukturiertes Feedback zu Ihrem Vorgehen.
""")

# Chat-Verlauf starten
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Guten Tag, ich bin froh, dass ich mich heute bei Ihnen vorstellen kann."}
    ]

# Chat anzeigen
for msg in st.session_state.messages[1:]:
    sender = "👩 Karina" if msg["role"] == "assistant" else "🧑 Du"
    st.markdown(f"**{sender}:** {msg['content']}")

# Eingabeformular
with st.form(key="eingabe_formular", clear_on_submit=True):
    user_input = st.text_input("Deine Frage an Karina:")
    submit_button = st.form_submit_button(label="Absenden")

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
    st.rerun()

# Körperliche Untersuchung
st.markdown("---")
st.subheader("Körperliche Untersuchung")

if "koerper_befund" not in st.session_state:
    st.session_state.koerper_befund = None

if st.button("🩺 Untersuchung durchführen"):
    untersuchung_prompt = """
Erstelle einen typischen körperlichen Untersuchungsbefund bei einer Patientin mit Morbus Crohn mit Ileitis terminalis. Verwende Fachsprache, aber vermeide jede Form von diagnostischer Interpretation oder Hinweis auf konkrete Erkrankungen (z. B. 'deutet auf Crohn hin' o. ä.).

Strukturiere den Befund bitte in Abschnitte wie:

**Allgemeinzustand:**  
**Abdomen:**  
**Leber/Milz:**  
**Auskultation Herz/Lunge:**  
**Haut:**  
**Extremitäten:**  

Formuliere sachlich, beschreibend und medizinisch korrekt – wie in einem klinischen Untersuchungsprotokoll. Vermeide Wertungen, Hypothesen oder diagnostische Zuordnungen.
"""
    with st.spinner("Untersuchungsbefund wird erstellt..."):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": untersuchung_prompt}],
            temperature=0.9
        )
        st.session_state.koerper_befund = response.choices[0].message.content

if st.session_state.koerper_befund:
    st.success("✅ Untersuchungsbefund erstellt")
    st.markdown(st.session_state.koerper_befund)

# Weiterführende Diagnostik
st.markdown("---")
st.subheader("Weiterführende Diagnostik und Entscheidungstraining")

if "diagnostik_step" not in st.session_state:
    st.session_state.diagnostik_step = 0

if not st.session_state.koerper_befund:
    st.info("ℹ️ Bitte führen Sie zuerst die körperliche Untersuchung durch, bevor Sie mit der Diagnostik fortfahren.")
else:
    if st.session_state.diagnostik_step == 0:
        with st.form("weiterdiagnostik"):
            ddx_input2 = st.text_area("Differentialdiagnosen", key="ddx_input2")
            diag_input = st.text_area("Diagnostische Maßnahmen", key="diag_input2")
            submitted = st.form_submit_button("Diagnostik abschicken")

        if submitted:
            st.session_state.user_ddx2 = ddx_input2
            st.session_state.user_diagnostics = diag_input
            st.session_state.diagnostik_step = 1
            st.rerun()

# Befunde generieren
if st.session_state.get("diagnostik_step") == 1:
    st.markdown("### Befunde zur gewählten Diagnostik")
    diagnostik_eingabe = st.session_state.get("user_diagnostics", "")
    ddx_eingabe = st.session_state.get("user_ddx2", "")

    if st.button("Befunde generieren lassen"):
        prompt_befunde = f"""
Ein Studierender hat bei einer Patientin (Anamnese typisch für Morbus Crohn mit Ileitis terminalis) folgende drei Differentialdiagnosen angegeben:

{ddx_eingabe}

Er hat außerdem folgende diagnostische Schritte vorgeschlagen:

{diagnostik_eingabe}

Generiere zu den genannten diagnostischen Maßnahmen typische Befunde für einen Morbus Crohn mit terminaler Ileitis. Falls bestimmte Untersuchungen nicht genannt wurden, ignoriere sie.

Erstelle:
1. **Laborbefunde** in tabellarischer Form (SI-Einheiten, mit Referenzwerten)
2. **Mikrobiologische Ergebnisse** (z. B. Stuhlkultur, Clostridien, Parasiten)
3. **Radiologische / sonografische Befunde** in der typischen Fachterminologie
4. **Endoskopische und histologische Befunde**, falls zutreffend

Formuliere sachlich und im Stil eines Arztbriefs oder Befundberichts.
"""
        with st.spinner("Befunde werden generiert..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_befunde}],
                temperature=0.5
            )
            befund_text = response.choices[0].message.content
        st.session_state.befunde = befund_text
        st.success("✅ Befunde generiert")
        st.markdown("### 📄 Ergebnisse:")
        st.markdown(befund_text)

# Diagnose und Therapie
if "befunde" in st.session_state and "final_step" not in st.session_state:
    st.markdown("### Diagnose und Therapieentscheidung")
    with st.form("diagnose_therapie"):
        final_diagnose = st.text_input("Ihre endgültige Diagnose:")
        therapie_vorschlag = st.text_area("Ihr Therapievorschlag:")
        submitted_final = st.form_submit_button("✅ Entscheidung abschließen")

    if submitted_final:
        st.session_state.final_diagnose = final_diagnose
        st.session_state.therapie_vorschlag = therapie_vorschlag
        st.session_state.final_step = True
        st.success("✅ Entscheidung gespeichert")

# Abschlussfeedback
if "final_step" in st.session_state:
    st.markdown("---")
    st.subheader("📋 Abschließende Evaluation")
    if st.button("📋 Abschluss-Feedback anzeigen"):
        ddx_text = st.session_state.get("user_ddx2", "")
        diag_text = st.session_state.get("user_diagnostics", "")
        befund_text = st.session_state.get("befunde", "")
        finale_diag = st.session_state.get("final_diagnose", "")
        therapie = st.session_state.get("therapie_vorschlag", "")
        karina_verlauf = "\n".join([
            msg["content"] for msg in st.session_state.messages
            if msg["role"] == "assistant"
        ])

        feedback_prompt_final = f"""
Ein Medizinstudierender hat eine vollständige virtuelle Fallbesprechung mit einer Patientin durchgeführt. Du bist ein erfahrener medizinischer Prüfer.

Gesprächsverlauf:
{karina_verlauf}

Körperlicher Untersuchungsbefund:
{st.session_state.koerper_befund}

Vorgeschlagene Differentialdiagnosen:
{ddx_text}

Gewünschte Diagnostik:
{diag_text}

Generierte Befunde:
{befund_text}

Finale Diagnose:
{finale_diag}

Therapievorschlag:
{therapie}

Bitte gib ein strukturiertes, medizinisch-wissenschaftlich fundiertes Feedback:

1. Wurden im Gespräch alle relevanten anamnestischen Informationen erhoben?
2. War die Diagnostik sinnvoll, vollständig und passend zu den DDx?
3. Sind die Befunde zutreffend interpretiert?
4. Ist die finale Diagnose nachvollziehbar?
5. Ist der Therapievorschlag leitliniengerecht und begründet?

⚖Berücksichtige zusätzlich:
- ökologische Aspekte (z. B. CO₂-Bilanz, Strahlenbelastung, Ressourcenverbrauch)
- ökonomische Sinnhaftigkeit (Kosten-Nutzen-Verhältnis)

Strukturiere dein Feedback klar, hilfreich und differenziert – wie ein Kommentar bei einer mündlichen Prüfung.
"""
        with st.spinner("Evaluation wird erstellt..."):
            eval_response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": feedback_prompt_final}],
                temperature=0.4
            )
            final_feedback = eval_response.choices[0].message.content
        st.session_state.final_feedback = final_feedback
        st.success("✅ Evaluation erstellt")
        st.markdown("### Abschlussfeedback:")
        st.markdown(final_feedback)

# Downloadbereich
st.markdown("---")
st.subheader("Download des Chatprotokolls und Feedback")
if "final_feedback" in st.session_state:
    protokoll = ""
    for msg in st.session_state.messages[1:]:
        rolle = "Karina" if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n\n"

    if "koerper_befund" in st.session_state:
        protokoll += "---\n🩺 Körperlicher Untersuchungsbefund:\n"
        protokoll += st.session_state.koerper_befund + "\n\n"

    protokoll += "---\n📄 Abschlussfeedback:\n"
    protokoll += st.session_state.final_feedback
    st.download_button(
        label="⬇️ Gespräch & Feedback herunterladen",
        data=protokoll,
        file_name="karina_chatprotokoll.txt",
        mime="text/plain"
    )
else:
    st.info("💬 Das Protokoll kann nach der Evaluation heruntergeladen werden.")
