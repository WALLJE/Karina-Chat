import streamlit as st
from datetime import datetime
import streamlit.components.v1 as components
from module.untersuchungsmodul import generiere_koerperbefund
from openai import RateLimitError

# Voraussetzungen prüfen
if (
    "diagnose_szenario" not in st.session_state or
    "patient_name" not in st.session_state or
    "patient_age" not in st.session_state or
    "patient_job" not in st.session_state or
    "diagnose_features" not in st.session_state
):
    st.warning("⚠️ Die Patientin wurde noch nicht initialisiert. Bitte starte über die Startseite.")
    st.stop()

# Titel
st.title(f"🩺 Körperliche Untersuchung bei {st.session_state.patient_name}")

# Optional: Startzeit merken (z. B. für spätere Auswertung)
if "start_untersuchung" not in st.session_state:
    st.session_state.start_untersuchung = datetime.now()

# Körperlicher Befund generieren oder anzeigen

# Bedingung: mindestens eine Anamnesefrage gestellt
fragen_gestellt = any(m["role"] == "user" for m in st.session_state.get("messages", []))

if "koerper_befund" in st.session_state:
    st.success("✅ Körperliche Untersuchung erfolgt.")
    st.subheader("🔍 Befund")
    st.markdown(f"<div style='background-color:#f0f5f3; padding: 1em; border-radius: 8px;'>"
                f"{st.session_state.koerper_befund}</div>", unsafe_allow_html=True)

elif fragen_gestellt:
    if st.button("🩺 Untersuchung durchführen"):
        with st.spinner(f"{st.session_state.patient_name} wird untersucht..."):
            try:
                koerper_befund = generiere_koerperbefund(
                    st.session_state["openai_client"],
                    st.session_state.diagnose_szenario,
                    st.session_state.diagnose_features,
                    st.session_state.get("koerper_befund_tip", "")
                )
                st.session_state.koerper_befund = koerper_befund
                st.rerun()
            except RateLimitError:
                st.error("🚫 Die Untersuchung konnte nicht erstellt werden. Die OpenAI-API ist derzeit überlastet.")
else:
    st.subheader("🩺 Körperliche Untersuchung")
    st.button("Untersuchung durchführen", disabled=True)
    st.info(f"Zuerst bitte mit {st.session_state.patient_name} sprechen.", icon="🔒")
    st.page_link("pages/1_Anamnese.py", label="Zurück zur Anamnese", icon="⬅")
    
# Verlauf sichern (optional für spätere Analyse)
if "untersuchung_done" not in st.session_state:
    st.session_state.untersuchung_done = True

# Trennlinie zum Navigationslink
st.markdown("---")

# Weiter-Link zur Diagnostik
# Hinweis: "href='/Diagnostik'" sorgt für internen Seitenwechsel, nicht für neues Fenster
st.page_link(
    "pages/4_Diagnostik.py",
    label="Weiter zur Diagnostik",
    icon="🧪",
    disabled="koerper_befund" not in st.session_state
)

if "koerper_befund" not in st.session_state:
    st.info(":grey[Dieser Schritt wird verfügbar, sobald die körperliche Untersuchung abgeschlossen ist.]", icon="🔒")

