
# Version 4.7
#  
# incl Zöliakie, Laktoseintoleranz
# To do
# Layout Antworten belassen
# Anamnese und Diagnostik wiederholen lassen.
# Läuft!

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
        "Appendizitis",
        "Zöliakie",
        "Laktoseintoleranz"
    ])

# Zufälliger Patientenname und Alter
if "patient_name" not in st.session_state:
    st.session_state.patient_name = random.choice([
        "Karina", "Leonie", "Sophie", "Laura", "Anna", "Mara"
    ])

if "patient_age" not in st.session_state:
    st.session_state.patient_age = random.randint(20, 34)

# Zufälliger Beruf
if "patient_job" not in st.session_state:
    st.session_state.patient_job = random.choice([
        "Studentin der Wirtschaftswissenschaften",
        "Erzieherin",
        "Elektronikerin",
        "Kunststudentin",
        "Polizistin"
    ])

# Begrüßungstext
#if "messages" not in st.session_state:
#    eintritt = f"{st.session_state.patient_name} ({st.session_state.patient_age} Jahre, {st.session_state.patient_job}) betritt den Raum."
#    start_text = "Guten Tag, ich bin froh, dass ich mich heute bei Ihnen vorstellen kann."
#    st.session_state.messages = [
#        {"role": "system", "content": f"Patientin: {st.session_state.patient_name}, {st.session_state.patient_age} Jahre alt, {st.session_state.patient_job}."},
#        {"role": "assistant", "content": eintritt},
#        {"role": "assistant", "content": start_text}
#    ]
  
#System-Prompt
if st.session_state.diagnose_szenario == "Morbus Crohn":
    SYSTEM_PROMPT = f"""
Patientensimulation - Morbus Crohn

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige {st.session_state.patient_job}.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Du leidest seit mehreren Monaten unter Bauchschmerzen im rechten Unterbauch. Diese treten schubweise auf. Gelegentlich hast du Fieber bis 38,5 °C und Nachtschweiß. Dein Stuhlgang ist breiig, und du musst 3–5 × täglich auf die Toilette. Du hast in der letzten Woche 3 kg ungewollt abgenommen.
Erzähle davon aber nur, wenn ausdrücklich danach gefragt wird.
Reisen: Vor 5 Jahren Korsika, sonst nur in Deutschland.
"""
elif st.session_state.diagnose_szenario == "Reizdarmsyndrom":
    SYSTEM_PROMPT = f"""
Patientensimulation – Reizdarmsyndrom

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige {st.session_state.patient_job}.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Du hast seit über 6 Monaten immer wieder Bauchschmerzen, mal rechts, mal links, aber nie in der Mitte. Diese bessern sich meist nach dem Stuhlgang. Manchmal hast du weichen Stuhl, manchmal Verstopfung. Es besteht kein Fieber und kein Gewichtsverlust. Dein Allgemeinbefinden ist gut, du bist aber beunruhigt, weil es chronisch ist.
Erzähle das nur auf Nachfrage. Reisen: In den letzten Jahren nur in Deutschland, vor Jahren mal in der Türkei, da hattest Du eine Magen-Darm-Infektion.
"""
elif st.session_state.diagnose_szenario == "Appendizitis":
    SYSTEM_PROMPT = f"""
Patientensimulation – Appendizitis

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige {st.session_state.patient_job}.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Seit etwa einem Tag hast du zunehmende Bauchschmerzen, die erst um den Nabel herum begannen und nun im rechten Unterbauch lokalisiert sind. Dir ist übel, du hattest keinen Appetit. Du hattest heute Fieber bis 38,3 °C. Du machst dir Sorgen. Der letzte Stuhlgang war gestern, normal.
Erzähle das nur auf gezielte Nachfrage. Reisen: Nur in Deutschland.
"""

elif st.session_state.diagnose_szenario == "Zöliakie":
    SYSTEM_PROMPT = f"""
Patientensimulation – Zöliakie

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige {st.session_state.patient_job}.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Seit mehreren Monaten hast Du wiederkehrend Bauchschmerzen, eigentlich hast Du schon viel länger Beschwerden: Blähungen, Durchfall. Manchmal ist Dir übel. Du machst dir Sorgen, auch weil Du Dich oft müde fühlst. Dein Stuhlgang riecht übel, auch wenn Winde abgehen. Manchmal hast Du juckenden Hautausschlag mit kleinen Bläschen. Du bist schon immer auffallend schlank und eher untergewichtig: dein BMI ist 17.
Erzähle das nur auf gezielte Nachfrage. Reisen: In den letzten Jahren nur in Europa unterwegs. 
"""

elif st.session_state.diagnose_szenario == "Laktoseintoleranz":
    SYSTEM_PROMPT = f"""
Patientensimulation – Laktoseintoleranz

Du bist {st.session_state.patient_name}, eine {st.session_state.patient_age}-jährige {st.session_state.patient_job}.
Beantworte Fragen grundsätzlich knapp und gib nur so viele Informationen preis, wie direkt erfragt wurden. 
Seit mehreren Monaten hast Du wiederkehrend Bauchschmerzen, viele Blähungen. Manchmal ist Dir nach dem Essen übel, Du hsat Schwindel und Kopfshcmerzen. Es kommt Dir so vor, dass Dir dasvor allem dann  passiert, wenn Du Milchprodukte zu Dir gneommen hast. Du machst dir Sorgen, auch weil Du Dich oft müde fühlst. Dein Stuhlgang riecht übel, auch wenn Winde abgehen. Dein Gewicht ist stabil.
Erzähle das nur auf gezielte Nachfrage. Reisen: Du reist gerne, vor 4 Moanten warst Du auf eine Kreuzfahrt im Mittelmeer. Familie: Dein Großvater ist mit 85 Jahren an Darmkrebs gestorben.
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
    eintritt = f"{st.session_state.patient_name} ({st.session_state.patient_age} Jahre), {st.session_state.patient_job}, betritt den Raum."
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

# Eingabeformular Anamnese Chat
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
st.markdown("---")
st.subheader("📄 Ergebnisse der diagnostischen Maßnahmen")

# aus diagnostik
#if "befunde" in st.session_state:
    # Befunde wurden schon erstellt – einfach anzeigen 
#    st.success("✅ Befunde wurden bereits erstellt.")
#    st.markdown(st.session_state.befunde)
#else:
    # Noch keine Befunde vorhanden – Button anbieten
#    if st.button("🧪 Befunde generieren lassen"):
#        if "user_diagnostics" in st.session_state:
#            diagnostik_eingabe = st.session_state.user_diagnostics
            # (weiter mit Befundgenerierung)
#        else:
#            st.warning("Bitte geben Sie zuerst diagnostische Maßnahmen ein, bevor Sie Befunde generieren.")

if "koerper_befund" in st.session_state:
    st.success("✅ Körperliche Untersuchung erfolgt.")
    st.markdown(st.session_state.befunde)
    # st.session_state.koerper_befund = None

else:
    st.button("🩺 Untersuchung durchführen")
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
    with st.spinner(f"{st.session_state.patient_name} wird untersucht..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": untersuchung_prompt}],
                temperature=0.5
            )
            st.session_state.koerper_befund = response.choices[0].message.content
        except RateLimitError:
            st.error("🚫 Die Untersuchung konnte nicht erstellt werden. Die OpenAI-API ist derzeit überlastet.")

# Wenn körperlicher Befund vorhanden
if st.session_state.get("koerper_befund"):
    st.success("✅ Untersuchungsbefund erstellt")
    st.markdown(st.session_state.koerper_befund)

    # Eingabeformular für Differentialdiagnosen und Diagnostik, falls noch nicht gemacht
    if "user_ddx2" not in st.session_state:
        st.markdown("---")
        st.subheader("🧠 Differentialdiagnosen und diagnostische Maßnahmen")

        with st.form("differentialdiagnosen_diagnostik_formular"):
            ddx_input2 = st.text_area("Welche drei Differentialdiagnosen halten Sie nach Anamnese und Untersuchung für möglich?", key="ddx_input2")
            diag_input2 = st.text_area("Welche konkreten diagnostischen Maßnahmen möchten Sie vorschlagen?", key="diag_input2")
            submitted_diag = st.form_submit_button("✅ Eingaben speichern")

        if submitted_diag:
            st.session_state.user_ddx2 = ddx_input2
            st.session_state.user_diagnostics = diag_input2
            st.success("✅ Angaben gespeichert. Befunde können jetzt generiert werden.")
            st.rerun()

# Wenn Differentialdiagnosen und Diagnostik schon gespeichert sind
if "user_ddx2" in st.session_state and "user_diagnostics" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Ihre gespeicherten Eingaben:")
    st.markdown(f"**Differentialdiagnosen:**\n{st.session_state.user_ddx2}")
    st.markdown(f"**Diagnostische Maßnahmen:**\n{st.session_state.user_diagnostics}")

# Befunde anzeigen oder generieren
st.markdown("---")
st.subheader("📄 Ergebnisse der diagnostischen Maßnahmen")

if "befunde" in st.session_state:
    # Befunde wurden schon erstellt – einfach anzeigen
    st.success("✅ Befunde wurden bereits erstellt.")
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
                st.rerun()
            except RateLimitError:
                st.error("🚫 Befunde konnten nicht generiert werden. Die OpenAI-API ist aktuell überlastet.")

            
# Diagnose und Therapie
if "befunde" in st.session_state and "final_step" not in st.session_state:
    st.markdown("### Diagnose und Therapiekonzept")
    with st.form("diagnose_therapie"):
        final_diagnose = st.text_input("Ihre endgültige Diagnose:")
        therapie_vorschlag = st.text_area("Ihr Therapiekonzept, bitte ggf. ausführlicher beschreiben:")
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
    st.markdown(f"Der Fall basierte auf der Diagnose: *{st.session_state.diagnose_szenario}*.")

    if st.button("📋 Abschluss-Feedback anzeigen"):
        # Alle Eingaben sicher abrufen
        user_ddx2 = st.session_state.get("user_ddx2", "Keine Differentialdiagnosen angegeben.")
        user_diagnostics = st.session_state.get("user_diagnostics", "Keine diagnostischen Maßnahmen angegeben.")
        befunde = st.session_state.get("befunde", "Keine Befunde generiert.")
        final_diagnose = st.session_state.get("final_diagnose", "Keine finale Diagnose eingegeben.")
        therapie_vorschlag = st.session_state.get("therapie_vorschlag", "Kein Therapiekonzept eingegeben.")

        # Nur die Fragen des Studierenden extrahieren
        user_verlauf = "\n".join([
            msg["content"] for msg in st.session_state.messages
            if msg["role"] == "user"
        ])

        # Feedback erstellen und zusammensetzen
        # muss eingerückt bleiben
        feedback_prompt_final = f"""
Ein Medizinstudierender hat eine vollständige virtuelle Fallbesprechung mit einer Patientin durchgeführt. Du bist ein erfahrener medizinischer Prüfer.

Beurteile ausschließlich die Eingaben und Entscheidungen des Studierenden – NICHT die Antworten der Patientin oder automatisch generierte Inhalte.

Die zugrunde liegende Erkrankung im Szenario lautet: **{st.session_state.diagnose_szenario}**.

Hier ist der Gesprächsverlauf mit den Fragen und Aussagen des Nutzers:
{user_verlauf}

Erhobene Differentialdiagnosen (Nutzerangaben):
{user_ddx2}

Geplante diagnostische Maßnahmen (Nutzerangaben):
{user_diagnostics}

GPT-generierte Befunde (nur als Hintergrund, bitte nicht bewerten):
{befunde}

Finale Diagnose (Nutzereingabe):
{final_diagnose}

Therapiekonzept (Nutzereingabe):
{therapie_vorschlag}

---
Strukturiere dein Feedback klar, hilfreich und differenziert – wie ein persönlicher Kommentar bei einer mündlichen Prüfung, schreibe in der zweiten Person.

1. Wurden im Gespräch alle relevanten anamnestischen Informationen erhoben?
2. War die gewählte Diagnostik nachvollziehbar, vollständig und passend zur Szenariodiagnose **{st.session_state.diagnose_szenario}**?
3. Ist die finale Diagnose nachvollziehbar, insbesondere im Hinblick auf Differenzierung zu anderen Möglichkeiten?
4. Ist das Therapiekonzept leitliniengerecht, plausibel und auf die Diagnose abgestimmt?

⚖ Berücksichtige zusätzlich:
- ökologische Aspekte (z. B. überflüssige Diagnostik, zuviele Anforderungen, CO₂-Bilanz, Strahlenbelastung bei CT oder Röntgen, Ressourcenverbrauch)
- ökonomische Sinnhaftigkeit (Kosten-Nutzen-Verhältnis)

"""
        # muss eingerückt bleiben
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
# Zusammenfassung und Download vorbereiten
st.markdown("---")
st.subheader("📄 Download des gesamten Gesprächsprotokolls")

if "final_feedback" in st.session_state:
    protokoll = ""

    # Szenario
    protokoll += f"🩺 Simuliertes Krankheitsbild: {st.session_state.diagnose_szenario}\n\n"

    # Gesprächsverlauf
    protokoll += "---\n💬 Gesprächsverlauf (nur Fragen des Studierenden):\n"
    for msg in st.session_state.messages[1:]:
        rolle = st.session_state.patient_name if msg["role"] == "assistant" else "Du"
        protokoll += f"{rolle}: {msg['content']}\n"

    # Körperlicher Untersuchungsbefund
    if "koerper_befund" in st.session_state:
        protokoll += "\n---\n🩺 Körperlicher Untersuchungsbefund:\n"
        protokoll += st.session_state.koerper_befund + "\n"

    # Differentialdiagnosen
    if "user_ddx2" in st.session_state:
        protokoll += "\n---\n🧠 Erhobene Differentialdiagnosen:\n"
        protokoll += st.session_state.user_ddx2 + "\n"

    # Diagnostische Maßnahmen
    if "user_diagnostics" in st.session_state:
        protokoll += "\n---\n🔬 Geplante diagnostische Maßnahmen:\n"
        protokoll += st.session_state.user_diagnostics + "\n"

    # Generierte Befunde
    if "befunde" in st.session_state:
        protokoll += "\n---\n📄 Ergebnisse der diagnostischen Maßnahmen:\n"
        protokoll += st.session_state.befunde + "\n"

    # Finale Diagnose
    if "final_diagnose" in st.session_state:
        protokoll += "\n---\n🩺 Finale Diagnose:\n"
        protokoll += st.session_state.final_diagnose + "\n"

    # Therapiekonzept
    if "therapie_vorschlag" in st.session_state:
        protokoll += "\n---\n💊 Therapiekonzept:\n"
        protokoll += st.session_state.therapie_vorschlag + "\n"

    # Abschlussfeedback
    protokoll += "\n---\n📋 Strukturierte Rückmeldung:\n"
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

