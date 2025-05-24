#Version 3

import streamlit as st
from openai import OpenAI

def diagnostik_und_befunde_routine(client: OpenAI, runde=1):
    st.markdown(f"### 🔎 Diagnostik – Termin {runde}")

    befund_existiert = f"befunde_runde_{runde}" in st.session_state
    aktive_runde = st.session_state.get("diagnostik_runden_gesamt", 1)

    # Eingabeformular NUR in aktiver Runde, wenn noch kein Befund existiert
    if runde == aktive_runde and not befund_existiert:
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
                st.success("✅ Zusätzliche Befunde erstellt")
                st.markdown(befund)

    # Bestehende Befunde anzeigen
    if befund_existiert:
        st.markdown("✅ **Befunde für diese Runde:**")
        st.markdown(st.session_state[f"befunde_runde_{runde}"])

    # Dokumentiere aktuelle Runde
    st.session_state["diagnostik_runden_gesamt"] = max(
        st.session_state.get("diagnostik_runden_gesamt", 1),
        runde
    )

    # Nur in aktiver Runde nach weiterer Diagnostik fragen
    if runde == aktive_runde and befund_existiert:
        weitere = st.radio(
            f"Möchten Sie weitere Diagnostik nach Runde {runde} anfordern?",
            ["Nein", "Ja"],
            key=f"weiter_diag_{runde}"
        )
        if weitere == "Ja":
            st.session_state["diagnostik_runden_gesamt"] = runde + 1
            return diagnostik_und_befunde_routine(client, runde=runde+1)

    # --- Zusammenfassung ---
    diagnostik_eingaben = ""
    gpt_befunde = ""

    # Runde 1 (außerhalb dieser Funktion)
    diag1 = st.session_state.get("user_diagnostics", "")
    bef1 = st.session_state.get("befunde", "")
    if diag1:
        diagnostik_eingaben += f"\n---\n### Runde 1\n{diag1}\n"
    if bef1:
        gpt_befunde += f"\n---\n### Runde 1\n{bef1}\n"

    # Weitere Runden
    gesamt = st.session_state.get("diagnostik_runden_gesamt", runde)
    for i in range(2, gesamt + 1):
        diag = st.session_state.get(f"diagnostik_runde_{i}", "")
        bef = st.session_state.get(f"befunde_runde_{i}", "")
        if diag:
            diagnostik_eingaben += f"\n---\n### Runde {i}\n{diag}\n"
        if bef:
            gpt_befunde += f"\n---\n### Runde {i}\n{bef}\n"

    return diagnostik_eingaben.strip(), gpt_befunde.strip()
