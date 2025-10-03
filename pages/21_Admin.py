import streamlit as st

from module.admin_data import FeedbackExportError, build_feedback_export
from module.sidebar import show_sidebar
from module.footer import copyright_footer


copyright_footer()
show_sidebar()

if not st.session_state.get("is_admin"):
    st.error("🚫 Kein Zugriff: Dieser Bereich steht nur Administrator*innen zur Verfügung.")
    st.info("Bitte gib in der Anamnese den gültigen Admin-Code ein, um Zugriff zu erhalten.")
    st.page_link("pages/1_Anamnese.py", label="⬅ Zurück zur Anamnese")
    st.stop()

st.title("Adminbereich")
st.markdown(
    "Hier entstehen künftig die administrativen Werkzeuge zur Verwaltung und Auswertung des Trainings.")

st.markdown("---")
st.subheader("Adminmodus")
st.write("Der Adminmodus ist aktiv. Bei Bedarf kannst du ihn hier wieder deaktivieren.")

if st.button("🔒 Adminmodus beenden", type="primary"):
    st.session_state["is_admin"] = False
    try:
        st.switch_page("pages/1_Anamnese.py")
    except Exception:
        st.experimental_set_query_params(page="1_Anamnese")
        st.rerun()

st.markdown("---")
st.header("📊 Auswertungen")
st.subheader("💾 Feedback-Export")

feedback_excel = None
feedback_filename = "feedback_gpt.xlsx"

with st.spinner("Supabase-Daten werden geladen..."):
    try:
        feedback_excel, feedback_filename = build_feedback_export()
    except FeedbackExportError as exc:
        feedback_excel = None
        st.error(f"🚫 Export nicht möglich: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        feedback_excel = None
        st.error(f"⚠️ Unerwarteter Fehler beim Export: {exc}")

if feedback_excel:
    st.download_button(
        "⬇️ Feedback-Daten als Excel herunterladen",
        data=feedback_excel,
        file_name=feedback_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

st.info("Platzhalter für statistische Übersichten und Reports.")

st.header("🛠️ Einstellungen")
st.info("Platzhalter für Konfigurationsoptionen und Benutzerverwaltung.")

st.header("🗂️ Ressourcen")
st.info("Platzhalter für Uploads, Downloads und Materialverwaltung.")
