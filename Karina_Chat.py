# Version 4.5
# To do: 
# mehr Fälle (Zöliakie, Laktoseintoleranz)
# Layout (Antworten belassen)
# Anamnese und Diagnostik wiederholen lassen.
#

import streamlit as st
from openai import OpenAI, RateLimitError
import os
import random

# API-Key setzen
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Zufällige Erkrankung und Name auswählen
if "diagnose_szenario" not in st.session_state:
    st.session_state.diagnose_szenario = random.choice([
        "Morbus Crohn",
        "Reizdarmsyndrom",
        "Appendizitis"
    ])

# Zufälliger Patientenname und Alter
if "patient_name" not in st.session_state:
    st.session_state.patient_name = random.choice([
        "Karina", "Leonie", "Sophie", "Laura", "Anna", "Mara"
    ])

if "patient_age" not in st.session_state:
    st.session_state.patient_age = random.randint(20, 34)
  
#System-Prompt
if st.session_state.diagnose_szenario == "Morbus Crohn":
    SYSTEM_PROMPT = """
Patientensimulation - Morbus Crohn

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige Studentin der Wirtschaftswissenschaften.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Du leidest seit mehreren Monaten unter Bauchschmerzen im rechten Unterbauch. Diese treten schubweise auf. Gelegentlich hast du Fieber bis 38,5 °C und Nachtschweiß. Dein Stuhlgang ist breiig, und du musst 3–5 × täglich auf die Toilette. Du hast in der letzten Woche 3 kg ungewollt abgenommen.
Erzähle davon aber nur, wenn ausdrücklich danach gefragt wird.
Reisen: Vor 5 Jahren Korsika, sonst nur in Deutschland.
"""
elif st.session_state.diagnose_szenario == "Reizdarmsyndrom":
    SYSTEM_PROMPT = """
Patientensimulation – Reizdarmsyndrom

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige Studentin der Wirtschaftswissenschaften.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Du hast seit über 6 Monaten immer wieder Bauchschmerzen, mal rechts, mal links, aber nie in der Mitte. Diese bessern sich meist nach dem Stuhlgang. Manchmal hast du weichen Stuhl, manchmal Verstopfung. Es besteht kein Fieber und kein Gewichtsverlust. Dein Allgemeinbefinden ist gut, du bist aber beunruhigt, weil es chronisch ist.
Erzähle das nur auf Nachfrage. Reisen: In den letzten Jahren nur in Deutschland, vor Jahren mal in der Türkei, da hattest Du eine Magen-Darm-Infektion.
"""
elif st.session_state.diagnose_szenario == "Appendizitis":
    SYSTEM_PROMPT = """
Patientensimulation – Appendizitis

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige Studentin der Wirtschaftswissenschaften.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Seit etwa einem Tag hast du zunehmende Bauchschmerzen, die erst um den Nabel herum begannen und nun im rechten Unterbauch lokalisiert sind. Dir ist übel, du hattest keinen Appetit. Du hattest heute Fieber bis 38,3 °C. Du machst dir Sorgen. Der letzte Stuhlgang war gestern, normal.
Erzähle das nur auf gezielte Nachfrage. Reisen: Nur in Deutschland.
"""

# Titel und Instruktion
st.title(f"Virtuelles Fallbeispiel")
st.info(f"""
**Instruktionen für Studierende:**

Sie führen ein strukturiertes Anamnesegespräch mit der virtuellen Patientin {st.session_state.patient_name}.
Geben Sie zum Beginn Ihre Fragen an die Patientin unten ein. Ziel ist es, durch gezieltes Nachfragen eine Verdachtsdiagnose zu stellen und sinnvolle weitere Diagnostik zu planen.

Bitte beachten Sie:
- {st.session_state.patient_name} antwortet nur auf das, was direkt gefragt wird.
- Medizinische Fachsprache versteht sie nicht unbedingt – erklären Sie unklare Begriffe.

Wenn Sie genug anamnestische Informationen erhoben haben:
- Führen Sie eine körperliche Untersuchung durch (per Button unten).
- Danach: Nennen Sie Ihre Differentialdiagnosen und die gewünschte Diagnostik.
- Sie erhalten typische Befunde und sollen dann eine Diagnose und ein Therapiekonzept festlegen. Erläurtern Sie die Therapie gern ausführlich.
- Danach erhalten Sie ein strukturiertes Feedback zu Ihrem Vorgehen.
""")

# Chat-Verlauf starten
if "messages" not in st.session_state:
    eintritt = f"{st.session_state.patient_name} ({st.session_state.patient_age} Jahre) betritt den Raum."
    start_text = "Guten Tag, ich bin froh, dass ich mich heute bei Ihnen vorstellen kann."
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": eintritt},
        {"role": "assistant", "content": start_text}
    ]


# Chat anzeigen
for msg in st.session_state.messages[1:]:
    sender = f"👩 {st.session_state.patient_name}" if msg["role"] == "assistant" else "🧑 Du"
    st.markdown(f"**{sender}:** {msg['content']}")

# Eingabeformular
with st.form(key="eingabe_formular", clear_on_submit=True):
    user_input = st.text_input(f"Deine Frage an {st.session_state.patient_name}:")
    submit_button = st.form_submit_button(label="Absenden")

if submit_button and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner(f"{st.session_state.patient_name} antwortet..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                temperature=0.6
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except RateLimitError:
            st.error("🚫 Die Anfrage konnte nicht verarbeitet werden, da die OpenAI-API derzeit überlastet ist. Bitte versuchen Sie es in einigen Minuten erneut.")
    st.rerun()

# Körperliche Untersuchung
st.markdown("---")
st.subheader("Körperliche Untersuchung")

if "koerper_befund" not in st.session_state:
    st.session_state.koerper_befund = None

if st.button("🩺 Untersuchung durchführen"):
    untersuchung_prompt = f"""
Die Patientin hat eine zufällig simulierte Erkrankung. Diese lautet: {st.session_state.diagnose_szenario}.

Erstelle einen körperlichen Untersuchungsbefund, der zu dieser Erkrankung passt, ohne sie explizit zu nennen oder zu diagnostizieren. Passe die Befundlage so an, dass sie klinisch konsistent ist, aber nicht interpretierend oder hinweisgebend wirkt.

Strukturiere den Befund bitte in folgende Abschnitte:

**Allgemeinzustand:**  
**Abdomen:**   
**Auskultation Herz/Lunge:**  
**Haut:**  
**Extremitäten:**  

Gib ausschließlich körperliche Untersuchungsbefunde an – keine Bildgebung, Labordiagnostik oder Zusatzverfahren. Vermeide jede Form von Bewertung, Hypothese oder Krankheitsnennung.

Formuliere neutral, präzise und sachlich – so, wie es in einem klinischen Untersuchungsprotokoll stehen würde.
"""
    with st.spinner("Untersuchungsbefund wird erstellt..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": untersuchung_prompt}],
                temperature=0.5
            )
            st.session_state.koerper_befund = response.choices[0].message.content
        except RateLimitError:
            st.error("🚫 Die Untersuchung konnte nicht erstellt werden. Die OpenAI-API ist derzeit überlastet.")

if st.session_state.koerper_befund:
    st.success("✅ Untersuchungsbefund erstellt")
    st.markdown(st.session_state.koerper_befund)

    if "diagnostik_step" not in st.session_state:
        st.session_state.diagnostik_step = 0

# Modul für Diagnosen und Diagnostik
# Befunde anzeigen oder generieren
st.markdown("---")
st.subheader("📄 Ergebnisse der diagnostischen Maßnahmen")

if "befunde" in st.session_state:
    # Befunde wurden schon erstellt – einfach anzeigen
    st.markdown(st.session_state.befunde)
else:
    # Noch keine Befunde vorhanden – Button anbieten
    if st.button("🧪 Befunde generieren lassen"):
        if "user_diagnostics" in st.session_state:
            diagnostik_eingabe = st.session_state.user_diagnostics
            # (weiter mit Befundgenerierung)
        else:
            st.warning("Bitte geben Sie zuerst diagnostische Maßnahmen ein, bevor Sie Befunde generieren.")

        diagnose_szenario = st.session_state.diagnose_szenario
        prompt_befunde = f"""
Die Patientin hat laut Szenario das Krankheitsbild **{diagnose_szenario}**.

Ein Medizinstudierender hat folgende diagnostische Maßnahmen konkret angefordert:

{diagnostik_eingabe}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen. Gib die Laborwerte in einer Tabelle aus:
**Parameter** | **Wert** | **Referenzbereich (nur SI-Einheit)**. 
Vermeide Interpretationen oder Diagnosen.

Gib die Befunde strukturiert und sachlich wieder. Ergänze keine nicht angeforderten Untersuchungen.
Beginne den Befund mit:
"Diese Befunde wurden automatisiert durch eine KI (GPT-4) erstellt und dienen der Simulation. Sie können unvollständig oder fehlerhaft sein."
"""

        with st.spinner(f"{st.session_state.patient_name} erstellt die Befunde..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt_befunde}],
                    temperature=0.5
                )
                st.session_state.befunde = response.choices[0].message.content
                st.success("✅ Befunde generiert")
                st.experimental_rerun()
            except RateLimitError:
                st.error("🚫 Befunde konnten nicht generiert werden. Die OpenAI-API ist aktuell überlastet.")

            
# Diagnose und Therapie
if "befunde" in st.session_state and "final_step" not in st.session_state:
    st.markdown("### Diagnose und Therapiekonzept")
    with st.form("diagnose_therapie"):
        final_diagnose = st.text_input("Ihre endgültige Diagnose:")
        therapie_vorschlag = st.text_area("Ihr Therapiekonzept:")
        submitted_final = st.form_submit_button("✅ Entscheidung abschließen")

    if submitted_final:
        st.session_state.final_diagnose = final_diagnose
        st.session_state.therapie_vorschlag = therapie_vorschlag
        st.session_state.final_step = True
        st.success("✅ Entscheidung gespeichert")

# Abschlussfeedback
if "final_step" in st.session_state:
    st.markdown("---")
    st.subheader("Abschlussbewertung zur ärztlichen Entscheidungsfindung")
    st.markdown(f"Der Fall basierte auf der zufällig gewählten Diagnose: *{st.session_state.diagnose_szenario}*.")

if st.button("📋 Abschluss-Feedback anzeigen"):
        ddx_text = st.session_state.get("user_ddx2", "")
        diag_text = st.session_state.get("user_diagnostics", "")
        befund_text = st.session_state.get("befunde", "")
        finale_diag = st.session_state.get("final_diagnose", "")
        therapie = st.session_state.get("therapie_vorschlag", "")

user_verlauf = "\n".join([
    msg["content"] for msg in st.session_state.messages
    if msg["role"] == "user"
])

feedback_prompt_final = f"""
Ein Medizinstudierender hat eine vollständige virtuelle Fallbesprechung mit einer Patientin durchgeführt. Du bist ein erfahrener medizinischer Prüfer.

Beurteile ausschließlich die Eingaben und Entscheidungen des Studierenden – NICHT die Antworten der Patientin oder automatisch generierte Inhalte.

Die zugrunde liegende Erkrankung im Szenario lautet: **{st.session_state.diagnose_szenario}**.

Hier ist der Gesprächsverlauf mit den Fragen und Aussagen des Studierenden (Nutzer):
{user_verlauf}

Erhobene Differentialdiagnosen (Nutzerangaben):
{st.session_state.user_ddx2}

Geplante diagnostische Maßnahmen (Nutzerangaben):
{st.session_state.user_diagnostics}

GPT-generierte Befunde (nur als Hintergrund, bitte nicht bewerten):
{st.session_state.befunde}

Finale Diagnose (Nutzereingabe):
{st.session_state.final_diagnose}

Therapiekonzept (Nutzereingabe):
{st.session_state.therapie_vorschlag}

---

Bitte gib ein strukturiertes, medizinisch-wissenschaftlich fundiertes Feedback zur Leistung des Studierenden:
Nenne zunächst die dem Fall zugrunde liegende Diagnose. Hat der Student die Diagnose richtig erfasst?
1. Wurden im Gespräch relevante anamnestische Informationen aktiv und strukturiert erhoben? Sei sehr kritisch bei zu wenig gestellten Frage zur Anamnese.
2. Passten die gewählten Differentialdiagnosen zur Szenario-Erkrankung?
3. Wurden sinnvolle, leitliniengerechte diagnostische Maßnahmen geplant?
4. Wurde eine nachvollziehbare und richtige finale Diagnose gestellt? Falls abweichend, war sie gut begründet?
5. Wurde ein angemessenes Therapiekonzept entwickelt (Akut- und Langzeitstrategie)?

⚖ Berücksichtige zusätzlich:
- ökologische Aspekte (z. B. CO₂-Bilanz, Strahlenbelastung, Ressourcenverbrauch)
- ökonomische Sinnhaftigkeit (Kosten-Nutzen-Verhältnis)

Strukturiere dein Feedback klar und verständlich – wie ein persönliches Kommentar an den Studierenden. Schreibe in der Du-Form.
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
st.markdown("### Strukturierte Rückmeldung zur Fallbearbeitung:")
st.markdown(final_feedback)

# Downloadbereich
st.markdown("---")
st.subheader("Download des Chatprotokolls und Feedback")
# Überprüft, ob final_feedback vorhanden ist
if "final_feedback" in st.session_state:
    protokoll = ""
    protokoll += f"🩺 Simuliertes Krankheitsbild: {st.session_state.diagnose_szenario}\n\n"
    protokoll += "---\n💬 Gesprächsverlauf:\n"
    
    for msg in st.session_state.messages[1:]:
        rolle = "Karina" if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n"
    
    # Hier können weitere Protokollteile wie Befunde etc. hinzugefügt werden
    if "koerper_befund" in st.session_state:
        protokoll += "\n---\n🩺 Körperlicher Untersuchungsbefund:\n"
        protokoll += st.session_state.koerper_befund + "\n"
    
    if "user_ddx2" in st.session_state:
        protokoll += "\n---\n🧠 Differentialdiagnosen:\n"
        protokoll += st.session_state.user_ddx2 + "\n"

    if "user_diagnostics" in st.session_state:
        protokoll += "\n---\n🔬 Gewünschte Diagnostik:\n"
        protokoll += st.session_state.user_diagnostics + "\n"

    if "befunde" in st.session_state:
        protokoll += "\n---\n📄 Generierte Befunde:\n"
        protokoll += st.session_state.befunde + "\n"
    
    protokoll += "\n---\n📄 Abschlussfeedback:\n"
    protokoll += st.session_state.final_feedback + "\n"

    # Download-Button zum Export des Protokolls
    st.download_button(
        label="⬇️ Gespräch & Feedback herunterladen",
        data=protokoll,
        file_name="karina_chatprotokoll.txt",
        mime="text/plain"
    )

else:
    st.info("💬 Das Protokoll kann nach der Evaluation heruntergeladen werden.")

