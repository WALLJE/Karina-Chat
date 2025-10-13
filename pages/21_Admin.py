import streamlit as st

from module.admin_data import FeedbackExportError, build_feedback_export
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline
from module.mcp_client import has_amboss_configuration
from module.fallverwaltung import (
    VERHALTENSOPTIONEN,
    fallauswahl_prompt,
    lade_fallbeispiele,
    prepare_fall_session_state,
    reset_fall_session_state,
    speichere_fallbeispiel,
)
from module.fall_config import (
    clear_fixed_behavior,
    clear_fixed_scenario,
    get_behavior_fix_state,
    get_fall_fix_state,
    set_fixed_behavior,
    set_fixed_scenario,
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
        "Im Offline-Modus werden statische Platzhalter statt KI-Antworten verwendet. "
        "Es werden keine externen LLM-Schnittstellen angesprochen."
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

st.subheader("Feedback-Modus")
amboss_available = has_amboss_configuration()
current_setting = st.session_state.get("use_amboss_feedback")
if current_setting is None:
    current_setting = amboss_available

amboss_toggle = st.toggle(
    "AMBOSS-Wissen in das Abschlussfeedback einbeziehen",
    value=current_setting,
    key="admin_amboss_feedback_toggle",
    disabled=is_offline() or not amboss_available,
    help=(
        "Aktiviere diese Option, um neben dem reinen ChatGPT-Feedback zusätzlich"
        " AMBOSS-Wissensdaten in die Bewertung einfließen zu lassen."
    ),
)

st.session_state["use_amboss_feedback"] = amboss_toggle

if not amboss_available:
    st.warning(
        "AMBOSS ist nicht konfiguriert. Hinterlege Zugangsdaten, um das kombinierte"
        " Feedback zu nutzen."
    )
elif is_offline():
    st.info(
        "Offline-Modus aktiv: Die Einstellung wird wirksam, sobald der Online-Modus"
        " reaktiviert ist."
    )
elif amboss_toggle:
    st.success("✅ Feedback-Modus: ChatGPT + AmbossMCP")
else:
    st.info("ℹ️ Feedback-Modus: Nur ChatGPT")

st.caption(
    "Aktuelle Einstellung: {label}.".format(
        label="ChatGPT + AmbossMCP" if st.session_state.get("use_amboss_feedback") else "Nur ChatGPT"
    )
)

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
        fixed, fixed_szenario = get_fall_fix_state()
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

        if fixed and fixed_szenario:
            modus_text = (
                "**Modus:** Fixierter Fall – alle Nutzer*innen bearbeiten aktuell "
                f"'{fixed_szenario}'."
            )
        else:
            modus_text = "**Modus:** Zufälliger Fall – neue Sitzungen erhalten ein zufälliges Szenario."

        if aktuelles_verhalten_kurz and aktuelles_verhalten_lang:
            verhalten_text = (
                "**Patient*innenverhalten:** "
                f"{aktuelles_verhalten_kurz.capitalize()} – {aktuelles_verhalten_lang}"
            )
        elif aktuelles_verhalten_lang:
            verhalten_text = f"**Patient*innenverhalten:** {aktuelles_verhalten_lang}"
        else:
            verhalten_text = "Für das aktuelle Szenario ist kein Verhalten gesetzt."

        st.info(f"{szenario_text}\n\n{modus_text}\n\n{verhalten_text}")

        with st.form("admin_fallauswahl"):
            if fixed and fixed_szenario in szenario_options:
                default_index = szenario_options.index(fixed_szenario)
            elif aktuelles_szenario in szenario_options:
                default_index = szenario_options.index(aktuelles_szenario)
            else:
                default_index = 0

            ausgewaehltes_szenario = st.selectbox(
                "Szenario auswählen",
                szenario_options,
                index=default_index,
                help="Wähle das Fallszenario aus, das für die nächste Sitzung verwendet werden soll.",
            )
            fall_fix_toggle = st.toggle(
                "Fall fixieren",
                value=fixed,
                help=(
                    "Aktiviere diese Option, damit alle künftigen Sitzungen dieses Szenario erhalten. "
                    "Wird die Fixierung aufgehoben, wählen nachfolgende Sitzungen wieder zufällig."
                ),
            )
            bestaetigt = st.form_submit_button("Szenario übernehmen", type="primary")

        if bestaetigt and ausgewaehltes_szenario:
            reset_fall_session_state()
            if fall_fix_toggle:
                fallauswahl_prompt(fall_df, ausgewaehltes_szenario)
                set_fixed_scenario(ausgewaehltes_szenario)
                st.session_state["admin_selected_szenario"] = ausgewaehltes_szenario
            else:
                clear_fixed_scenario()
                st.session_state.pop("admin_selected_szenario", None)
                fallauswahl_prompt(fall_df)
            prepare_fall_session_state()
            try:
                st.switch_page("pages/1_Anamnese.py")
            except Exception:
                st.rerun()

    st.subheader("Verhaltensoptionen")
    verhaltensoption_keys = list(VERHALTENSOPTIONEN.keys())
    behavior_fixed, aktuelles_verhalten = get_behavior_fix_state()

    vorauswahl_verhalten = st.session_state.get("patient_verhalten_memo") or aktuelles_verhalten
    if vorauswahl_verhalten in verhaltensoption_keys:
        verhalten_index = verhaltensoption_keys.index(vorauswahl_verhalten)
    else:
        verhalten_index = 0

    with st.form("admin_verhaltensoptionen"):
        ausgewaehltes_verhalten = st.selectbox(
            "Verhaltensoption auswählen",
            verhaltensoption_keys,
            index=verhalten_index,
            format_func=lambda key: f"{key} – {VERHALTENSOPTIONEN[key]}",
            help=(
                "Wähle, wie sich die Patient*innen in der Konversation verhalten sollen. "
                "Ohne Fixierung erfolgt weiterhin eine zufällige Auswahl."
            ),
        )
        verhalten_fix_toggle = st.toggle(
            "Verhalten fixieren",
            value=behavior_fixed,
            help=(
                "Aktiviere die Fixierung, um künftige Sitzungen mit dieser Verhaltensoption zu starten. "
                "Fixierungen laufen nach vier Stunden automatisch aus."
            ),
        )
        verhalten_bestaetigt = st.form_submit_button("Verhalten übernehmen", type="primary")

    if verhalten_bestaetigt:
        st.session_state["patient_verhalten_memo"] = ausgewaehltes_verhalten
        st.session_state["patient_verhalten"] = VERHALTENSOPTIONEN[ausgewaehltes_verhalten]
        if verhalten_fix_toggle:
            set_fixed_behavior(ausgewaehltes_verhalten)
            st.session_state["admin_selected_behavior"] = ausgewaehltes_verhalten
        else:
            clear_fixed_behavior()
            st.session_state.pop("admin_selected_behavior", None)
        prepare_fall_session_state()
        try:
            st.switch_page("pages/1_Anamnese.py")
        except Exception:
            st.rerun()

    st.divider()
    st.subheader("Neues Fallbeispiel")

    formular_state_key = "admin_fallformular_offen"
    if formular_state_key not in st.session_state:
        st.session_state[formular_state_key] = False

    if st.button("Neues Fallbeispiel hinzufügen", type="secondary"):
        st.session_state[formular_state_key] = True

    if st.session_state.get(formular_state_key):
        if st.button("Abbrechen", type="secondary"):
            st.session_state[formular_state_key] = False
            for key in list(st.session_state.keys()):
                if key.startswith("admin_neuer_fall_"):
                    st.session_state[key] = ""
            st.rerun()

        erforderliche_spalten = [
            "Szenario",
            "Beschreibung",
            "Körperliche Untersuchung",
            "Alter",
            "Geschlecht",
        ]

        vorhandene_spalten = list(fall_df.columns) if not fall_df.empty else []
        optionale_spalten = [
            spalte for spalte in vorhandene_spalten if spalte not in erforderliche_spalten
        ]

        for spalte in erforderliche_spalten:
            if spalte not in vorhandene_spalten:
                vorhandene_spalten.append(spalte)

        for spalte in erforderliche_spalten + optionale_spalten:
            state_key = f"admin_neuer_fall_{spalte}"
            if state_key not in st.session_state:
                st.session_state[state_key] = ""

        with st.form("admin_neues_fallbeispiel"):
            formularwerte: dict[str, str] = {}

            for spalte in erforderliche_spalten:
                widget_key = f"admin_neuer_fall_{spalte}"
                if spalte in {"Beschreibung", "Körperliche Untersuchung"}:
                    formularwerte[spalte] = st.text_area(spalte, key=widget_key)
                else:
                    formularwerte[spalte] = st.text_input(spalte, key=widget_key)

            for spalte in optionale_spalten:
                widget_key = f"admin_neuer_fall_{spalte}"
                formularwerte[spalte] = st.text_input(spalte, key=widget_key)

            abgesendet = st.form_submit_button("Fallbeispiel speichern", type="primary")

        if abgesendet:
            fehlermeldungen: list[str] = []
            neuer_fall: dict[str, object] = {}

            for spalte in erforderliche_spalten:
                wert = formularwerte.get(spalte, "")
                if not str(wert).strip():
                    fehlermeldungen.append(f"Bitte fülle das Feld '{spalte}' aus.")
                else:
                    neuer_fall[spalte] = str(wert).strip()

            for spalte in optionale_spalten:
                optional_wert = str(formularwerte.get(spalte, "")).strip()
                neuer_fall[spalte] = optional_wert if optional_wert else None

            alter_wert = str(neuer_fall.get("Alter", "")).strip()
            if alter_wert:
                try:
                    neuer_fall["Alter"] = int(float(alter_wert))
                except ValueError:
                    fehlermeldungen.append("Das Feld 'Alter' muss eine Zahl sein.")

            if fehlermeldungen:
                st.error("\n".join(fehlermeldungen))
            else:
                aktualisiert, fehler = speichere_fallbeispiel(
                    neuer_fall, pfad="fallbeispiele.xlsx"
                )
                if fehler:
                    st.error(f"Speichern fehlgeschlagen: {fehler}")
                elif aktualisiert is None:
                    st.error("Speichern fehlgeschlagen: Unerwarteter Fehler.")
                else:
                    fall_df = aktualisiert
                    st.success("Fallbeispiel wurde erfolgreich gespeichert.")
                    st.session_state[formular_state_key] = False
                    for key in list(st.session_state.keys()):
                        if key.startswith("admin_neuer_fall_"):
                            st.session_state[key] = ""

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

