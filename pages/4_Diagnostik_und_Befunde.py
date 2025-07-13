import streamlit as st
from module.sidebar import show_sidebar
from Karina_Chat_2 import copyright_footer
from diagnostikmodul import diagnostik_und_befunde_routine
from befundmodul import generiere_befund

show_sidebar()
st.page_link("karina_chat2", label="⬅ Zur Startseite", icon="🏠")

st.title("🤪 Diagnostik und Befunde")

# --- Voraussetzungen wie in Hauptdatei beachten ---
if "koerper_befund" in st.session_state:
    st.subheader("Differentialdiagnosen und diagnostische Maßnahmen")

    if "user_ddx2" not in st.session_state:
        with st.form("differentialdiagnosen_diagnostik_formular"):
            ddx_input2 = st.text_area("Welche drei Differentialdiagnosen halten Sie nach Anamnese und Untersuchung für möglich?", key="ddx_input2")
            diag_input2 = st.text_area("Welche konkreten diagnostischen Maßnahmen möchten Sie vorschlagen?", key="diag_input2")
            submitted_diag = st.form_submit_button("✅ Eingaben speichern")

        if submitted_diag:
            from sprachmodul import sprach_check
            client = st.session_state.get("openai_client")
            st.session_state.user_ddx2 = sprach_check(ddx_input2, client)
            st.session_state.user_diagnostics = sprach_check(diag_input2, client)
            st.rerun()

    else:
        st.markdown(f"**Differentialdiagnosen:**  \n{st.session_state.user_ddx2}")
        st.markdown(f"**Diagnostische Maßnahmen:**  \n{st.session_state.user_diagnostics}")
else:
    st.subheader("Differentialdiagnosen und diagnostische Maßnahmen")
    st.button("Untersuchung durchführen", disabled=True)
    st.info("❗Bitte führen Sie zuerst die körperliche Untersuchung durch.")

# --- Befunde anzeigen oder generieren ---
st.markdown("---")

if (
    "koerper_befund" in st.session_state
    and "user_diagnostics" in st.session_state
    and "user_ddx2" in st.session_state
):
    st.subheader("📄 Befunde")

    if "befunde" in st.session_state:
        st.markdown(st.session_state.befunde)
    else:
        if st.button("🧪 Befunde generieren lassen"):
            try:
                diagnostik_eingabe = st.session_state.user_diagnostics
                diagnose_szenario = st.session_state.diagnose_szenario
                client = st.session_state.get("openai_client")

                with st.spinner("Befunde werden generiert..."):
                    befund = generiere_befund(client, diagnose_szenario, diagnostik_eingabe)

                st.session_state.befunde = befund
                st.success("✅ Befunde generiert")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Fehler bei der Befundgenerierung: {e}")
else:
    st.subheader("📄 Befunde")
    st.button("🧪 Befunde generieren lassen", disabled=True)
    st.info("❗Bitte führen Sie zuerst die körperliche Untersuchung durch.")

# Weitere Diagnostik-Termine
if not st.session_state.get("final_diagnose", "").strip():
    if (
        "diagnostik_eingaben" not in st.session_state
        or "gpt_befunde" not in st.session_state
        or st.session_state.get("diagnostik_aktiv", False)
    ):
        client = st.session_state.get("openai_client")
        diagnostik_eingaben, gpt_befunde = diagnostik_und_befunde_routine(
            client,
            start_runde=2,
            weitere_diagnostik_aktiv=False
        )
        st.session_state["diagnostik_eingaben"] = diagnostik_eingaben
        st.session_state["gpt_befunde"] = gpt_befunde
    else:
        diagnostik_eingaben = st.session_state["diagnostik_eingaben"]
        gpt_befunde = st.session_state["gpt_befunde"]

    # Anzeige bestehender Befunde
    gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
    for i in range(2, gesamt + 1):
        bef_key = f"befunde_runde_{i}"
        bef = st.session_state.get(bef_key, "")
        if bef:
            st.markdown(f"📅 Termin {i}")
            st.markdown(bef)

# Zusätzlicher Termin
gesamt = st.session_state.get("diagnostik_runden_gesamt", 1)
neuer_termin = gesamt + 1

if (
    st.session_state.get("diagnostik_aktiv", False)
    and f"diagnostik_runde_{neuer_termin}" not in st.session_state
):
    st.markdown(f"### 📅 Termin {neuer_termin}")
    with st.form(key=f"diagnostik_formular_runde_{neuer_termin}_hauptskript"):
        neue_diagnostik = st.text_area(
            "Welche zusätzlichen diagnostischen Maßnahmen möchten Sie anfordern?",
            key=f"eingabe_diag_r{neuer_termin}"
        )
        submitted = st.form_submit_button("✅ Diagnostik anfordern")

    if submitted and neue_diagnostik.strip():
        neue_diagnostik = neue_diagnostik.strip()
        st.session_state[f"diagnostik_runde_{neuer_termin}"] = neue_diagnostik

        szenario = st.session_state.get("diagnose_szenario", "")
        client = st.session_state.get("openai_client")
        with st.spinner("GPT erstellt Befunde..."):
            befund = generiere_befund(client, szenario, neue_diagnostik)
            st.session_state[f"befunde_runde_{neuer_termin}"] = befund
            st.session_state["diagnostik_runden_gesamt"] = neuer_termin
            st.session_state["diagnostik_aktiv"] = False
            st.rerun()

# Button für neue Diagnostik
if (
    not st.session_state.get("diagnostik_aktiv", False)
    and ("befunde" in st.session_state or gesamt >= 2)
):
    if st.button("➕ Weitere Diagnostik anfordern", key="btn_neue_diagnostik"):
        st.session_state["diagnostik_aktiv"] = True
        st.rerun()

# # Nur für Admin sichtbar:
# if st.session_state.get("admin_mode"):
#     st.page_link("pages/20_Fallbeispiel_Editor.py", label="🔧 Fallbeispiel-Editor", icon="🔧")

copyright_footer()

