import streamlit as st
from module.sidebar import show_sidebar
from module.navigation import redirect_to_start_page
from sprachmodul import sprach_check
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline

show_sidebar()
display_offline_banner()

st.subheader("Diagnose und Therapie")

# Steuerflag für den Bearbeitungsmodus der finalen Angaben.
# Falls aktiv, werden die Eingabefelder mit den bereits gespeicherten Werten vorbelegt,
# damit die Nutzer:innen ihre Diagnose/Therapie gezielt ergänzen oder korrigieren können.
st.session_state.setdefault("diagnose_therapie_edit", False)
# Synchronisations-Flag, das beim Wechsel in den Bearbeitungsmodus gesetzt wird.
# Es sorgt dafür, dass die Widget-States *vor* dem Rendern der Eingabefelder
# zuverlässig mit den aktuell korrigierten Werten befüllt werden.
st.session_state.setdefault("diagnose_therapie_sync_edit", False)
# Das finale Therapiesetting wird hier als eigenständiger Kontext gepflegt.
# Wir nutzen eine gültige Default-Option, damit das Radio-Widget keinen
# ungültigen Session-State-Wert verarbeitet.
# Debugging-Hinweis: Bei inkonsistenten UI-Zuständen kann dieser Key gezielt
# geleert werden, um die Auswahl neu zu erzwingen.
st.session_state.setdefault("therapie_setting_final", "Einweisung Notaufnahme")
# Synchronisations-Keys für die Eingabefelder, damit nach der sprachlichen Korrektur
# die aktualisierten Inhalte sicher in den Widgets angezeigt werden.
# Hinweis zum Debugging: Bei unerwarteten Vorbelegungen können diese Keys gezielt
# gelöscht werden (z.B. per st.session_state.pop(...)), um das Verhalten zu prüfen.
if "diagnose_therapie_edit_diag" not in st.session_state:
    st.session_state["diagnose_therapie_edit_diag"] = st.session_state.get("final_diagnose", "")
if "diagnose_therapie_edit_therapie" not in st.session_state:
    st.session_state["diagnose_therapie_edit_therapie"] = st.session_state.get("therapie_vorschlag", "")

# Voraussetzung: Befunde vorhanden
if "befunde" not in st.session_state:
    redirect_to_start_page(
        "⚠️ Bitte führe zuerst die Diagnostik durch und kehre anschließend hierher zurück."
    )

# Abschnitt: Diagnose und Therapie-Eingabe
if (
    st.session_state.get("final_diagnose", "").strip()
    and st.session_state.get("therapie_vorschlag", "").strip()
    and st.session_state.get("therapie_setting_final", "").strip()
    and not st.session_state.get("diagnose_therapie_edit")
):
    st.markdown(f"**Ihre Diagnose:**  \n{st.session_state.final_diagnose}")
    st.markdown(f"**Therapiekonzept:**  \n{st.session_state.therapie_vorschlag}")
    st.markdown(
        f"**Therapiesetting (final):**  \n{st.session_state.therapie_setting_final}"
    )
    # Wenn das Setting eine Einweisung verlangt, erläutern wir den Rollenwechsel.
    if st.session_state.therapie_setting_final in {"Einweisung Notaufnahme", "Einweisung elektiv"}:
        st.info(
            "ℹ️ **Rollenwechsel:** Die Versorgung erfolgt im Krankenhaus/Notaufnahme. "
            "Ab jetzt beziehen sich Diagnostik- und Therapieentscheidungen auf "
            "dieses Setting – Sie übernehmen die Rolle in der Klinik."
        )
    # Button, um gezielt zur Eingabe zurückzukehren und die bestehenden Inhalte zu bearbeiten.
    if st.button("✏️ Diagnose/Therapie überarbeiten oder ergänzen"):
        st.session_state.diagnose_therapie_edit = True
        # Synchronisation anfordern, damit die Widget-States im *nächsten* Lauf
        # vor dem Rendern der Eingabefelder auf die aktuell gespeicherten Werte
        # gesetzt werden können (Streamlit erlaubt keine Änderung nach Instanziierung).
        st.session_state.diagnose_therapie_sync_edit = True
        st.rerun()
else:
    # Synchronisation der Eingabefelder *vor* deren Instanziierung.
    # Damit wird sichergestellt, dass die korrigierten Inhalte tatsächlich in den
    # Widgets landen und keine veralteten Eingaben überschreiben.
    if st.session_state.get("diagnose_therapie_sync_edit"):
        st.session_state["diagnose_therapie_edit_diag"] = st.session_state.get("final_diagnose", "")
        st.session_state["diagnose_therapie_edit_therapie"] = st.session_state.get("therapie_vorschlag", "")
        st.session_state["diagnose_therapie_sync_edit"] = False
    with st.form("diagnose_therapie_formular"):
        # Vorbelegung der Texteingaben, wenn bereits Werte vorhanden sind.
        # Dies ermöglicht ein schnelles Nachschärfen der Inhalte ohne erneute Eingabe.
        input_diag = st.text_input(
            "Ihre endgültige Diagnose:",
            key="diagnose_therapie_edit_diag",
        )
        input_therapie = st.text_area(
            "Ihr Therapiekonzept:",
            key="diagnose_therapie_edit_therapie",
        )
        # Das finale Therapiesetting wird hier neu bewertet. Der zusätzliche
        # Facharzt-Termin ist bewusst nur im finalen Setting enthalten.
        setting_optionen_final = [
            "Einweisung Notaufnahme",
            "Einweisung elektiv",
            "ambulant (zeitnahe Wiedervorstellung)",
            "ambulant (Vorstellung im nächsten Quartal)",
            "Vorstellung Facharzt (Termin in 2 Monaten)",
        ]
        bestehendes_setting = st.session_state.get("therapie_setting_final", "")
        if bestehendes_setting in setting_optionen_final:
            default_index = setting_optionen_final.index(bestehendes_setting)
        else:
            default_index = 0
        setting_final = st.radio(
            "Wie soll die Therapie endgültig fortgeführt werden?",
            options=setting_optionen_final,
            index=default_index,
            key="therapie_setting_final",
        )
        # Wenn eine Einweisung gewählt wird, erklären wir den Rollenwechsel
        # direkt im Formular, damit die Studierenden den Kontext früh verstehen.
        if setting_final in {"Einweisung Notaufnahme", "Einweisung elektiv"}:
            st.info(
                "ℹ️ **Rollenwechsel:** Die weitere Versorgung erfolgt im Krankenhaus/Notaufnahme. "
                "Bitte richten Sie Diagnostik- und Therapievorschläge konsequent an diesem Setting aus."
            )
        submitted_final = st.form_submit_button("✅ Senden")

    if submitted_final:
        client = st.session_state.get("openai_client")
        st.session_state.final_diagnose = sprach_check(input_diag, client)
        st.session_state.therapie_vorschlag = sprach_check(input_therapie, client)
        # Das finale Setting wird separat gespeichert, um es im Feedback
        # und in der Supabase-Persistenz auswerten zu können.
        st.session_state.therapie_setting_final = setting_final
        # Nach dem Speichern wieder in die Anzeigeansicht wechseln.
        st.session_state.diagnose_therapie_edit = False
        if is_offline():
            st.info("🔌 Offline-Modus: Eingaben wurden ohne GPT-Korrektur übernommen.")
        st.rerun()

# # Nur für Admin sichtbar:
# if st.session_state.get("admin_mode"):
#     st.page_link("pages/20_Fallbeispiel_Editor.py", label="🔧 Fallbeispiel-Editor", icon="🔧")

# Weiter-Link zum Feedback
st.page_link(
    "pages/6_Feedback.py",
    label="Weiter zum Feedback",
    icon="📝",
    disabled=not (
        st.session_state.get("final_diagnose", "").strip() and
        st.session_state.get("therapie_vorschlag", "").strip() and
        st.session_state.get("therapie_setting_final", "").strip()
    )
)


copyright_footer()
