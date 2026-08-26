# Version 10 (korrigiert)
#

import streamlit as st
from openai import OpenAI
from sprachmodul import sprach_check
from befundmodul import generiere_befund
from module.offline import is_offline
from module.loading_indicator import task_spinner

def aktualisiere_diagnostik_zusammenfassung(start_runde=2):
    """Erstellt die kumulative Zusammenfassung aller Diagnostik- und Befund-Runden und speichert sie im SessionState."""
    diagnostik_eingaben = ""
    gpt_befunde = ""

# Termin 1: Basisdiagnostik
    erster_diag = st.session_state.get("user_diagnostics", "")
    erster_befund = st.session_state.get("befunde", "")
    
    if erster_diag or erster_befund:
        diagnostik_eingaben += f"\n---\n### Termin 1\n{erster_diag}\n"
        gpt_befunde += f"\n---\n### Termin 1\n{erster_befund}\n"
        
    # Jetzt die restlichen Runden (ab Runde 2)
    for i in range(2, st.session_state.get("diagnostik_runden_gesamt", start_runde - 1) + 1):
        diag = st.session_state.get(f"diagnostik_runde_{i}", "")
        bef = st.session_state.get(f"befunde_runde_{i}", "")
        if diag:
            diagnostik_eingaben += f"\n---\n### Termin {i}\n{diag}\n"
        if bef:
            gpt_befunde += f"\n---\n### Termin {i}\n{bef}\n"

    # Der unveränderte Text dient als Basis für spätere Kombinationen mit
    # gesondert angeforderten Untersuchungen und kann bei Bedarf separat
    # exportiert werden.
    basistext = diagnostik_eingaben.strip()
    st.session_state["diagnostik_eingaben_basis"] = basistext

    sonder_text = st.session_state.get("sonderdiagnostik_text", "").strip()
    if sonder_text and basistext:
        diagnostik_eingaben = f"{basistext}\n\n{sonder_text}"
    elif sonder_text:
        diagnostik_eingaben = sonder_text
    else:
        diagnostik_eingaben = basistext

    # Die zusätzlichen körperlichen Untersuchungen liefern eigene Befundfragmente,
    # die im Supabase-Export unter "Befunde" auftauchen sollen. Wir hängen sie
    # daher getrennt vom Basistext an und behalten so die ursprüngliche Termin-
    # Struktur bei.
    sonder_befund_text = st.session_state.get("sonderdiagnostik_befund_text", "").strip()
    if sonder_befund_text:
        if gpt_befunde:
            gpt_befunde = f"{gpt_befunde}\n\n{sonder_befund_text}"
        else:
            gpt_befunde = sonder_befund_text

    st.session_state["diagnostik_eingaben_kumuliert"] = diagnostik_eingaben.strip()
    st.session_state["gpt_befunde_kumuliert"] = gpt_befunde.strip()


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

                if is_offline():
                    befund = generiere_befund(client, szenario, neue_diagnostik)
                    st.session_state[befund_key] = befund
                else:
                    ladeaufgaben = [
                        "Übermittle neue Diagnostik",
                        "Analysiere Fallkontext",
                        "Erstelle ergänzenden Befund",
                    ]
                    with task_spinner(f"Diagnostik für {st.session_state.get('patient_name', 'Patientin')} wird ausgewertet...", ladeaufgaben) as indikator:
                        indikator.advance(1)
                        befund = generiere_befund(client, szenario, neue_diagnostik)
                        indikator.advance(1)
                        st.session_state[befund_key] = befund
                        indikator.advance(1)

                st.session_state["diagnostik_runden_gesamt"] = runde
                st.session_state["diagnostik_aktiv"] = False  # zurücksetzen
                st.rerun()

# 🔁 Zusammenfassung aller Runden
    aktualisiere_diagnostik_zusammenfassung(start_runde)
    return (
        st.session_state["diagnostik_eingaben_kumuliert"],
        st.session_state["gpt_befunde_kumuliert"]
    )

   
