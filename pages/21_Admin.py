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

DEFAULT_EXPORT_FILENAME = "feedback_gpt.xlsx"


def _reset_feedback_export_state() -> None:
    """Ensure the feedback export values are always valid bytes and filename."""

    st.session_state["feedback_export_bytes"] = b""
    st.session_state["feedback_export_filename"] = DEFAULT_EXPORT_FILENAME


def _prepare_feedback_export() -> None:
    with st.spinner("Supabase-Daten werden geladen..."):
        try:
            export_bytes, export_filename = build_feedback_export()
        except FeedbackExportError as exc:
            _reset_feedback_export_state()
            st.error(f"🚫 Export nicht möglich: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            _reset_feedback_export_state()
            st.error(f"⚠️ Unerwarteter Fehler beim Export: {exc}")
        else:
            if not isinstance(export_bytes, (bytes, bytearray)):
                _reset_feedback_export_state()
                st.error("⚠️ Ungültige Exportdaten erhalten. Bitte erneut versuchen.")
            else:
                st.session_state["feedback_export_bytes"] = bytes(export_bytes)
                st.session_state["feedback_export_filename"] = export_filename or DEFAULT_EXPORT_FILENAME


existing_bytes = st.session_state.get("feedback_export_bytes")
if isinstance(existing_bytes, bytearray):
    st.session_state["feedback_export_bytes"] = bytes(existing_bytes)
elif not isinstance(existing_bytes, bytes):
    _reset_feedback_export_state()

if not isinstance(st.session_state.get("feedback_export_filename"), str):
    st.session_state["feedback_export_filename"] = DEFAULT_EXPORT_FILENAME

if st.button("🔄 Feedback-Export aktualisieren", type="secondary"):
    _prepare_feedback_export()

export_bytes = st.session_state.get("feedback_export_bytes", b"") or b""
export_filename = st.session_state.get("feedback_export_filename", DEFAULT_EXPORT_FILENAME) or DEFAULT_EXPORT_FILENAME
download_ready = bool(export_bytes)

st.download_button(
    "⬇️ Feedback-Daten als Excel herunterladen",
    data=export_bytes,
    file_name=export_filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    key="feedback_export_button",
    disabled=not download_ready,
)

if download_ready:
    st.success("Der aktuelle Feedback-Export steht zum Download bereit.")
else:
    st.info("Bitte aktualisiere den Export, bevor du die Excel-Datei herunterlädst.")

st.info("Platzhalter für statistische Übersichten und Reports.")

st.header("🛠️ Einstellungen")
st.info("Platzhalter für Konfigurationsoptionen und Benutzerverwaltung.")

st.header("🗂️ Ressourcen")
st.info("Platzhalter für Uploads, Downloads und Materialverwaltung.")
