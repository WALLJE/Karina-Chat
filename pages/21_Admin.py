import streamlit as st

from module.admin_data import FeedbackExportError, build_feedback_export
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline
from module.fallverwaltung import (
    fallauswahl_prompt,
    lade_fallbeispiele,
    prepare_fall_session_state,
    reset_fall_session_state,
)


copyright_footer()
show_sidebar()
display_offline_banner()


def _restart_application_after_offline() -> None:
    """Reset den Session State und startet die Anwendung neu."""

    reset_fall_session_state()
    preserve_keys = {"offline_mode", "is_admin"}
    for key in list(st.session_state.keys()):
        if key in preserve_keys:
            continue
        st.session_state.pop(key, None)
    st.rerun()

if not st.session_state.get("is_admin"):
    st.error("Kein Zugriff: Dieser Bereich steht nur Administrator*innen zur Verfügung.")
    st.info("Bitte gib in der Anamnese den gültigen Admin-Code ein, um Zugriff zu erhalten.")
    st.page_link("pages/1_Anamnese.py", label="Zurück zur Anamnese")
    st.stop()

st.title("Adminbereich")

st.subheader("Verbindungsmodus")
current_offline = is_offline()
offline_toggle = st.toggle(
    "Offline-Modus aktivieren",
    value=current_offline,
    help=(
        "Im Offline-Modus werden statische Platzhalter statt GPT-Antworten verwendet. "
        "Die OpenAI-API wird dabei nicht angesprochen."
    ),
    key="admin_offline_toggle",
)

if offline_toggle != current_offline:
    st.session_state["offline_mode"] = offline_toggle
    if offline_toggle:
        st.info("Offline-Modus aktiviert. Alle Seiten nutzen jetzt statische Inhalte.")
    else:
        st.info("Online-Modus reaktiviert. Die Anwendung wird neu gestartet.")
        _restart_application_after_offline()

st.subheader("Adminmodus")
st.write("Der Adminmodus ist aktiv. Bei Bedarf kannst du ihn hier wieder deaktivieren.")

if st.button("Adminmodus beenden", type="primary"):
    st.session_state["is_admin"] = False
    try:
        st.switch_page("pages/1_Anamnese.py")
    except Exception:
        st.experimental_set_query_params(page="1_Anamnese")
        st.rerun()

st.subheader("Fallverwaltung")

fall_df = lade_fallbeispiele(pfad="fallbeispiele.xlsx")

if fall_df.empty:
    st.info("Die Fallliste konnte nicht geladen werden. Bitte prüfe die Datei 'fallbeispiele.xlsx'.")
elif "Szenario" not in fall_df.columns:
    st.error("Die Fallliste enthält keine Spalte 'Szenario'.")
else:
    szenario_options = sorted(
        {str(s).strip() for s in fall_df["Szenario"].dropna() if str(s).strip()}
    )

    if not szenario_options:
        st.info("In der Datei wurden keine Szenarien gefunden.")
    else:
        aktuelles_szenario = st.session_state.get("diagnose_szenario") or st.session_state.get(
            "admin_selected_szenario"
        )
        aktuelles_verhalten_kurz = st.session_state.get("patient_verhalten_memo")
        aktuelles_verhalten_lang = st.session_state.get("patient_verhalten")

        szenario_text = (
            f"**Aktuelles Szenario:** {aktuelles_szenario}"
            if aktuelles_szenario
            else "Aktuell ist kein Szenario geladen."
        )

        if aktuelles_verhalten_kurz and aktuelles_verhalten_lang:
            verhalten_text = (
                "**Patient*innenverhalten:** "
                f"{aktuelles_verhalten_kurz.capitalize()} – {aktuelles_verhalten_lang}"
            )
        elif aktuelles_verhalten_lang:
            verhalten_text = f"**Patient*innenverhalten:** {aktuelles_verhalten_lang}"
        else:
            verhalten_text = "Für das aktuelle Szenario ist kein Verhalten gesetzt."

        st.info(f"{szenario_text}\n\n{verhalten_text}")

        with st.form("admin_fallauswahl"):
            ausgewaehltes_szenario = st.selectbox(
                "Szenario auswählen",
                szenario_options,
                help="Wähle das Fallszenario aus, das für die nächste Sitzung verwendet werden soll.",
            )
            bestaetigt = st.form_submit_button("Szenario übernehmen", type="primary")

        if bestaetigt and ausgewaehltes_szenario:
            reset_fall_session_state()
            fallauswahl_prompt(fall_df, ausgewaehltes_szenario)
            prepare_fall_session_state()
            st.session_state["admin_selected_szenario"] = ausgewaehltes_szenario
            try:
                st.switch_page("pages/1_Anamnese.py")
            except Exception:
                st.rerun()

st.subheader("Feedback-Export")

DEFAULT_EXPORT_FILENAME = "feedback_gpt.xlsx"

def _reset_feedback_export_state() -> None:
    """Ensure the feedback export values stay valid and consistent."""

    st.session_state["feedback_export_bytes"] = b""
    st.session_state["feedback_export_filename"] = DEFAULT_EXPORT_FILENAME


def _prepare_feedback_export() -> None:
    """Build the feedback export and keep the UI state in sync."""

    st.session_state["feedback_export_error"] = ""
    with st.spinner("Supabase-Daten werden geladen..."):
        try:
            export_bytes, export_filename = build_feedback_export()
        except FeedbackExportError as exc:
            _reset_feedback_export_state()
            st.session_state["feedback_export_error"] = f"Export nicht möglich: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            _reset_feedback_export_state()
            st.session_state["feedback_export_error"] = f"Unerwarteter Fehler beim Export: {exc}"
        else:
            if not isinstance(export_bytes, (bytes, bytearray)):
                _reset_feedback_export_state()
                st.session_state[
                    "feedback_export_error"
                ] = "Ungültige Exportdaten erhalten. Bitte erneut versuchen."
            else:
                st.session_state["feedback_export_bytes"] = bytes(export_bytes)
                st.session_state["feedback_export_filename"] = (
                    export_filename or DEFAULT_EXPORT_FILENAME
                )
                st.session_state["feedback_export_revision"] += 1


if "feedback_export_bytes" not in st.session_state:
    _reset_feedback_export_state()

if not isinstance(st.session_state.get("feedback_export_bytes"), bytes):
    _reset_feedback_export_state()

if "feedback_export_revision" not in st.session_state:
    st.session_state["feedback_export_revision"] = 0

if "feedback_export_error" not in st.session_state:
    st.session_state["feedback_export_error"] = ""

if st.button("Feedback-Export aktualisieren", type="secondary"):
    _reset_feedback_export_state()
    _prepare_feedback_export()

export_bytes = st.session_state.get("feedback_export_bytes", b"") or b""
export_filename = (
    st.session_state.get("feedback_export_filename", DEFAULT_EXPORT_FILENAME)
    or DEFAULT_EXPORT_FILENAME
)
download_ready = bool(export_bytes)
download_key = f"feedback_export_button_{st.session_state['feedback_export_revision']}"

download_placeholder = st.empty()

if download_ready:
    download_placeholder.download_button(
        "Feedback-Daten als Excel herunterladen",
        data=export_bytes,
        file_name=export_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        key=download_key,
    )
    st.success("Der aktuelle Feedback-Export steht zum Download bereit.")
else:
    download_placeholder.button(
        "Feedback-Daten als Excel herunterladen",
        disabled=True,
        key=f"{download_key}_placeholder",
    )
    st.info("Bitte aktualisiere den Export, bevor du die Excel-Datei herunterlädst.")

if st.session_state.get("feedback_export_error"):
    st.error(st.session_state["feedback_export_error"])
