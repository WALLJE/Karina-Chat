# Version 7 (korrigiert)
#

import streamlit as st
from openai import OpenAI

def diagnostik_und_befunde_routine(client: OpenAI, start_runde=2):
    # aktuelle Runde bestimmen (aus Session-State oder Default)
    aktive_runde = st.session_state.get("diagnostik_runden_gesamt", start_runde - 1)
    
    # Durchlaufe alle bisherigen Runden plus eine neue
    for runde in range(start_runde, aktive_runde + 2):
        befund_existiert = f"befunde_runde_{runde}" in st.session_state

        # Debug-Ausgabe
        st.write(f"🛠️ Runde: {runde}, Aktive Runde: {aktive_runde}, Key: diagnostik_formular_runde_{runde}")

        # Eingabeformular nur in nächster Runde anzeigen, wenn noch kein Befund vorhanden ist
        if (
            not befund_existiert
            and runde == aktive_runde + 1
            and st.session_state.get("diagnostik_aktiv", False)
        ):

            with st.form(f"diagnostik_formular_runde_{runde}"):
                neue_diagnostik = st.text_area("Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern?")
                submitted = st.form_submit_button("✅ Diagnostik anfordern")

            if submitted and neue_diagnostik.strip():
                neue_diagnostik = neue_diagnostik.strip()
                st.session_state[f"diagnostik_runde_{runde}"] = neue_diagnostik

                szenario = st.session_state.get("diagnose_szenario", "")
                prompt = f"""Die Patientin hat laut Szenario: {szenario}.
Folgende zusätzliche Diagnostik wurde angefordert:\n{neue_diagnostik}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen. Falls **Laborwerte** angefordert wurden, gib diese **ausschließlich in einer strukturierten Tabelle** aus, verwende dabei das Internationale Einheitensystem (SI) und folgendes Tabellenformat:

**Parameter** | **Wert** | **Referenzbereich (SI-Einheit)**. 

**Wichtig:** Interpretationen oder Diagnosen sind nicht erlaubt. Nenne auf keinen Fall das Diagnose-Szenario. Bewerte oder diskutiere nicht die Anforderungen.

Gib die Befunde strukturiert und sachlich wieder. Ergänze keine nicht angeforderten Untersuchungen."""

                with st.spinner("GPT erstellt Befunde..."):
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.4
                    )
                    befund = response.choices[0].message.content
                    st.session_state[f"befunde_runde_{runde}"] = befund
                    st.session_state["diagnostik_runden_gesamt"] = runde
                    st.session_state["diagnostik_aktiv"] = False  # ← FLAG zurücksetzen
                    st.rerun()

        # Bereits vorhandene Befunde anzeigen
        if befund_existiert:
            st.markdown(st.session_state[f"befunde_runde_{runde}"])

    # --- Zusammenfassung aller Befunde ---
    diagnostik_eingaben = ""
    gpt_befunde = ""

    # Runde 1 aus Hauptprogramm
    diag1 = st.session_state.get("user_diagnostics", "")
    bef1 = st.session_state.get("befunde", "")
    if diag1:
        diagnostik_eingaben += f"\n---\n### Termin 1\n{diag1}\n"
    if bef1:
        gpt_befunde += f"\n---\n### Termin 1\n{bef1}\n"

    gesamt = st.session_state.get("diagnostik_runden_gesamt", start_runde - 1)
    for i in range(2, gesamt + 1):
        diag = st.session_state.get(f"diagnostik_runde_{i}", "")
        bef = st.session_state.get(f"befunde_runde_{i}", "")
        if diag:
            diagnostik_eingaben += f"\n---\n### Termin {i}\n{diag}\n"
        if bef:
            gpt_befunde += f"\n---\n### Termin {i}\n{bef}\n"

    return diagnostik_eingaben.strip(), gpt_befunde.strip()
