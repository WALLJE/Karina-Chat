# diagnostikmodul.py

import streamlit as st
from openai import OpenAI

def diagnostik_und_befunde_routine(client: OpenAI, runde=1):
    st.markdown(f"### 🔎 Diagnostik - Termin {runde}")
    
    with st.form(f"diagnostik_formular_runde_{runde}"):
        neue_diagnostik = st.text_area("Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern?")
        submitted = st.form_submit_button("✅ Diagnostik anfordern")

    if submitted and neue_diagnostik.strip():
        neue_diagnostik = neue_diagnostik.strip()
        st.session_state[f"diagnostik_runde_{runde}"] = neue_diagnostik

        szenario = st.session_state.get("diagnose_szenario", "")
        prompt = f"""Die Patientin hat laut Szenario: {szenario}.
Folgende zusätzliche Diagnostik wurde angefordert:\n{neue_diagnostik}

Erstelle ausschließlich Befunde zu den genannten Untersuchungen. Falls **Laborwerte** angefordert wurden, gib  diese **ausschliesslich in einer strukturierten Tabelle** aus, verwende dabei immer das Internationale Einheitensystem SI und dieses Tabellenformat:

**Parameter** | **Wert** | **Referenzbereich (SI-Einheit)**. 

**Wichtig:** Interpretationen oder das Nennen von Diagnosen sind nicht erlaubt. Nenne auf keinen Fall das Diagnose-Szenario. Bewerte oder diskutiere nicht die Anforderungen.

Gib die Befunde strukturiert und sachlich wieder. Ergänze keine nicht angeforderten Untersuchungen. Erstelle ausschließlich Befunde zu diesen Maßnahmen."""

        with st.spinner("GPT erstellt Befunde..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            befund = response.choices[0].message.content
            st.session_state[f"befunde_runde_{runde}"] = befund
            st.success("✅ Zusätzliche Befunde erstellt")
            st.markdown(befund)

    if st.session_state.get(f"befunde_runde_{runde}", ""):
        weitere = st.radio(f"Möchten Sie weitere Untersuchungen anfordern?", ["Nein", "Ja"], key=f"weiter_diag_{runde}")
        if weitere == "Ja":
            diagnostik_und_befunde_routine(client, runde=runde+1)
