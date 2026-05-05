import streamlit as st
from module.sidebar import show_sidebar
from module.navigation import redirect_to_start_page, render_next_page_link
from sprachmodul import sprach_check
from module.footer import copyright_footer
from module.offline import display_offline_banner, is_offline

show_sidebar()
display_offline_banner()

# TODO: Debug-Ausgaben später entfernen.
# st.write("Debug Seite 5 > Session-Keys (Start):", sorted(st.session_state.keys()))
# st.write(
#     "Debug Seite 5 > therapie_setting-Keys (Start):",
#     [key for key in st.session_state.keys() if "therapie_setting" in key],
# )

st.subheader("Diagnose und Therapie")

# Steuerflag für den Bearbeitungsmodus der finalen Angaben.
st.session_state.setdefault("diagnose_therapie_edit", False)

# Synchronisations-Flag, das beim Wechsel in den Bearbeitungsmodus gesetzt wird.
st.session_state.setdefault("diagnose_therapie_sync_edit", False)

# Persistente Kopie des finalen Settings, damit der Wert nach dem Verlassen
# des Selectbox-Widgets erhalten bleibt.
if (
    "therapie_setting_final_persisted" in st.session_state
    and "therapie_setting_final" not in st.session_state
):
    st.session_state["therapie_setting_final"] = st.session_state[
        "therapie_setting_final_persisted"
    ]

# Das finale Therapiesetting wird hier als eigenständiger Kontext gepflegt.
st.session_state.setdefault(
    "therapie_setting_final",
    st.session_state.get("therapie_setting_final_persisted", "Einweisung Notaufnahme"),
)

# Synchronisations-Keys für die Eingabefelder
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
    # Button, um gezielt zur Eingabe zurückzukehren und die bestehenden Inhalte zu bearbeiten.
    if st.button("✏️ Diagnose/Therapie überarbeiten oder ergänzen"):
        st.session_state.diagnose_therapie_edit = True
        st.session_state.diagnose_therapie_sync_edit = True
        st.rerun()
else:
    # Synchronisation der Eingabefelder *vor* deren Instanziierung.
    if st.session_state.get("diagnose_therapie_sync_edit"):
        st.session_state["diagnose_therapie_edit_diag"] = st.session_state.get("final_diagnose", "")
        st.session_state["diagnose_therapie_edit_therapie"] = st.session_state.get("therapie_vorschlag", "")
        st.session_state["diagnose_therapie_sync_edit"] = False
        
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
        st.session_state.pop("therapie_setting_final", None)
        default_index = 0
        
    # --- Neues Layout Versorgungssetting ---
    st.markdown("<br>**Wie soll die Therapie endgültig fortgeführt werden?**", unsafe_allow_html=True)
    setting_final = st.selectbox(
        "Versorgungssetting",
        options=setting_optionen_final,
        index=default_index,
        key="therapie_setting_final",
        label_visibility="collapsed"
    )

    with st.expander("ℹ️ Hinweise zum gewählten Versorgungssetting", expanded=False):
        st.markdown(
            "💡 **Hinweis:** Prüfen Sie Ihr Vorgehen noch einmal und passen Sie das "
            "Versorgungssetting bei Bedarf an – Sie dürfen Ihre Einschätzung aus dem Diagnostik-Schritt "
            "hier bewusst revidieren.\n\n"
        )
        if setting_final.startswith("ambulant") or "Facharzt" in setting_final:
            st.markdown(
                "**Hinweis zur Therapie (ambulant):**\n\n"
                "Bitte formulieren Sie im Feld 'Therapiekonzept' alle Maßnahmen für die ambulante Weiterbehandlung (z.B. Medikamente, Rezeptierung, Krankschreibung, Verhaltenshinweise)."
            )
        else:
            st.markdown(
                "**Hinweis zur Therapie (Einweisung/Notaufnahme):**\n\n"
                "Bitte formulieren Sie im Feld 'Therapiekonzept', welche konkreten therapeutischen Schritte stationär als nächstes erfolgen sollen."
            )
    # --- Ende Neues Layout ---

    with st.form("diagnose_therapie_formular"):
        # Vorbelegung der Texteingaben, wenn bereits Werte vorhanden sind.
        input_diag = st.text_input(
            "Ihre endgültige Diagnose:",
            key="diagnose_therapie_edit_diag",
        )
        input_therapie = st.text_area(
            "Ihr Therapiekonzept:",
            key="diagnose_therapie_edit_therapie",
        )
        submitted_final = st.form_submit_button("✅ Senden")

    st.session_state["debug_snapshot_therapie_setting_final"] = st.session_state.get(
        "therapie_setting_final", ""
    )
    
    st.session_state["therapie_setting_final_persisted"] = st.session_state.get(
        "therapie_setting_final", ""
    )

    if submitted_final:
        client = st.session_state.get("openai_client")
        st.session_state.final_diagnose = sprach_check(input_diag, client)
        st.session_state.therapie_vorschlag = sprach_check(input_therapie, client)
        
        st.session_state.diagnose_therapie_edit = False
        if is_offline():
            st.info("🔌 Offline-Modus: Eingaben wurden ohne GPT-Korrektur übernommen.")
        st.rerun()


# Weiter-Link zum Feedback
st.markdown(
    """
    <style>
    div.st-key-weiter-feedback button[kind="secondary"] {
        background-color: #22a06b;
        color: #ffffff;
        border: 1px solid #1b7f54;
        border-radius: 0.75rem;
        font-weight: 600;
        padding: 0.6rem 1rem;
    }

    div.st-key-weiter-feedback button[kind="secondary"]:hover {
        background-color: #1b7f54;
        border-color: #166c47;
    }

    div.st-key-weiter-feedback button[kind="secondary"]:disabled {
        background-color: #d5d8de;
        color: #5d6573;
        border: 1px solid #bcc2cc;
        cursor: not-allowed;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

render_next_page_link(
    "pages/6_Feedback.py",
    label="Weiter zum Feedback",
    icon="📝",
    disabled=not (
        st.session_state.get("final_diagnose", "").strip() and
        st.session_state.get("therapie_vorschlag", "").strip() and
        st.session_state.get("therapie_setting_final", "").strip()
    ),
    as_button=True,
    button_key="weiter-feedback",
)

copyright_footer()
