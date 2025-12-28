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
    and not st.session_state.get("diagnose_therapie_edit")
):
    st.markdown(f"**Ihre Diagnose:**  \n{st.session_state.final_diagnose}")
    st.markdown(f"**Therapiekonzept:**  \n{st.session_state.therapie_vorschlag}")
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
        submitted_final = st.form_submit_button("✅ Senden")

    if submitted_final:
        client = st.session_state.get("openai_client")
        st.session_state.final_diagnose = sprach_check(input_diag, client)
        st.session_state.therapie_vorschlag = sprach_check(input_therapie, client)
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
        st.session_state.get("therapie_vorschlag", "").strip()
    )
)


copyright_footer()
