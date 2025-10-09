import streamlit as st
from module.sidebar import show_sidebar
from sprachmodul import sprach_check
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline
from module.llm_state import (
    ConfigurationError,
    MCPClientError,
    ensure_llm_client,
    get_provider_label,
)

show_sidebar()
display_offline_banner()

st.subheader("Diagnose und Therapie")

# Voraussetzung: Befunde vorhanden
if "befunde" not in st.session_state:
    st.error("❗Bitte führen Sie zuerst die Diagnostik durch.")
    st.stop()

# Abschnitt: Diagnose und Therapie-Eingabe
if st.session_state.get("final_diagnose", "").strip() and st.session_state.get("therapie_vorschlag", "").strip():
    st.markdown(f"**Ihre Diagnose:**  \n{st.session_state.final_diagnose}")
    st.markdown(f"**Therapiekonzept:**  \n{st.session_state.therapie_vorschlag}")
else:
    with st.form("diagnose_therapie_formular"):
        input_diag = st.text_input("Ihre endgültige Diagnose:")
        input_therapie = st.text_area("Ihr Therapiekonzept:")
        submitted_final = st.form_submit_button("✅ Senden")

    if "mcp_client" not in st.session_state and not is_offline():
        try:
            ensure_llm_client()
        except ConfigurationError as exc:
            st.warning(
                "⚙️ Die Konfiguration für {provider} ist unvollständig."
                " Die Seite wechselt in den Offline-Modus.\n\n"
                f"Details: {exc}".format(provider=get_provider_label())
            )
            st.session_state["offline_mode"] = True
            st.session_state["mcp_client"] = None
        except MCPClientError as exc:
            st.error(
                "❌ Der LLM-Client konnte nicht initialisiert werden. Bitte prüfe die "
                "aktuellen Zugangsdaten oder die Netzwerkverbindung.\n\n"
                f"Fehlerdetails: {exc}"
            )
            st.stop()

    if submitted_final:
        client = st.session_state.get("mcp_client")
        st.session_state.final_diagnose = sprach_check(input_diag, client)
        st.session_state.therapie_vorschlag = sprach_check(input_therapie, client)
        if is_offline():
            st.info("🔌 Offline-Modus: Eingaben wurden ohne GPT-Korrektur übernommen.")
        st.rerun()

# # Nur für Admin sichtbar:
# if st.session_state.get("admin_mode"):
#     st.page_link("pages/20_Fallbeispiel_Editor.py", label="🔧 Fallbeispiel-Editor", icon="🔧")

# Weiter-Link zum Feedback
st.page_link(
    "pages/6_Feedback_und_Evaluation.py",
    label="Weiter zur Auswertung & Feedback",
    icon="📝",
    disabled=not (
        st.session_state.get("final_diagnose", "").strip() and
        st.session_state.get("therapie_vorschlag", "").strip()
    )
)

if not (
    st.session_state.get("final_diagnose", "").strip() and
    st.session_state.get("therapie_vorschlag", "").strip()
):
    st.info(":grey[Dieser Schritt wird verfügbar, sobald Diagnose und Therapiekonzept eingegeben wurden.]", icon="🔒")


copyright_footer()

