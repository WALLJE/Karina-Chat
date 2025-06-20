# Version 7 (korrigiert)
#

import streamlit as st
from openai import OpenAI
from sprachmodul import sprach_check
from befundmodul import generiere_befund

def diagnostik_und_befunde_routine(client: OpenAI, start_runde=2, weitere_diagnostik_aktiv=False):
    # Ermittle höchste vorhandene Befund-Runde
    vorhandene_runden = [
        int(k.split("_")[-1])
        for k in st.session_state.keys()
        if k.startswith("befunde_runde_") and k.split("_")[-1].isdigit()
    ]
    max_befund_runde = max(vorhandene_runden, default=start_runde - 1)

    # Wenn neue Diagnostik aktiviert wurde, nächste Runde erlauben
    if st.session_state.get("diagnostik_aktiv", False):
        max_befund_runde += 1

    for runde in range(start_runde, max_befund_runde + 1):
        befund_key = f"befunde_runde_{runde}"
        befund_existiert = befund_key in st.session_state

        # Debug
        # st.write(f"📅 Termin: {runde}")

        # 📝 Eingabeformular nur, wenn explizit aktiviert
        if (
            not befund_existiert
            and runde not in vorhandene_runden
            and st.session_state.get("diagnostik_aktiv", False)
            and weitere_diagnostik_aktiv  # <-- neue Kontrolle, amit macht das Modul nur dann neue Formulare, wenn es explizit zulässt.
        ):
            with st.form(f"diagnostik_formular_runde_{runde}"):
                neue_diagnostik = st.text_area("Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern?")
                submitted = st.form_submit_button("✅ Diagnostik anfordern")

            if submitted and neue_diagnostik.strip():
                neue_diagnostik = sprach_check(neue_diagnostik.strip(), client)
                st.session_state[f"diagnostik_runde_{runde}"] = neue_diagnostik

                szenario = st.session_state.get("diagnose_szenario", "")

                with st.spinner("GPT erstellt Befunde..."):
                    befund = generiere_befund(client, szenario, neue_diagnostik)                
                    st.session_state[befund_key] = befund
                    st.session_state["diagnostik_runden_gesamt"] = runde
                    st.session_state["diagnostik_aktiv"] = False  # zurücksetzen
                    st.rerun()

# 🔁 Zusammenfassung aller Runden
    
    diagnostik_eingaben = ""
    gpt_befunde = ""

    for i in range(1, st.session_state.get("diagnostik_runden_gesamt", start_runde - 1) + 1):
        diag = st.session_state.get(f"diagnostik_runde_{i}", "")
        bef = st.session_state.get(f"befunde_runde_{i}", "")
        if diag:
            diagnostik_eingaben += f"\n---\n### Termin {i}\n{diag}\n"
        if bef:
            gpt_befunde += f"\n---\n### Termin {i}\n{bef}\n"


    return diagnostik_eingaben.strip(), gpt_befunde.strip()
