import base64
from pathlib import Path
from typing import Callable, Optional

import streamlit as st

from module.patient_language import get_patient_forms

# Der Pfad zum AMBOSS-Logo wird relativ zu dieser Datei bestimmt, damit auch bei
# alternativen Startverzeichnissen von Streamlit das Bild zuverlässig gefunden
# wird. Fallback-Mechanismen sind nicht nötig, da ein fehlendes Bild direkt
# durch ``st.image`` sichtbar wird.
AMBOSS_BILD_PFAD = Path(__file__).resolve().parents[1] / "pics" / "amboss_logo.png"


def _lade_amboss_logo_data_uri() -> str:
    """Gibt einen ``data:``-URI für das AMBOSS-Bild zurück."""
    bild_bytes = AMBOSS_BILD_PFAD.read_bytes()
    return f"data:image/png;base64,{base64.b64encode(bild_bytes).decode('utf-8')}"


AMBOSS_LOGO_DATA_URI = _lade_amboss_logo_data_uri()


def zeige_instruktionen_vor_start(lade_callback: Optional[Callable[[], None]] = None) -> None:
    """Blendet die Einstiegsinstruktionen ein und steuert den Ladeablauf."""

    st.session_state.setdefault("instruktion_bestätigt", False)
    st.session_state.setdefault("instruktion_loader_fertig", False)
    
    instruktionen_placeholder = st.empty()
    ladebereich = st.container()
    fortsetzen_placeholder = st.empty()

    def schreibe_instruktionen() -> None:
        """Erzeugt den Instruktionstext mit dynamischen Personenangaben."""
        patient_forms = get_patient_forms()
        patient_name = st.session_state.get("patient_name", "").strip()
        
        if patient_name:
            patient_intro = (
                "Sie übernehmen die Rolle einer Ärztin oder eines Arztes im Gespräch mit **"
                f"{patient_name}**, {patient_forms.relative_pronoun()} sich in Ihrer hausärztlichen Sprechstunde vorstellt."
            )
        else:
            patient_intro = (
                "Sie übernehmen die Rolle einer Ärztin oder eines Arztes im Gespräch mit einer simulierten Patientin "
                f"bzw. einem simulierten Patienten, {patient_forms.relative_pronoun()} sich in Ihrer hausärztlichen Sprechstunde vorstellt."
            )

        with instruktionen_placeholder.container():
            
            # --- Teil 1: Rolle und Ziel (Optisch hervorgehoben) ---
            st.info(f"""
            **Ihre Rolle:** {patient_intro}

            **Ihr Ziel:** Durch gezielte Anamnese und klinisches Denken eine Verdachtsdiagnose stellen sowie ein sinnvolles diagnostisches und therapeutisches Vorgehen entwickeln.
            """, icon="🩺")

            # --- Teil 2: Ablauf ---
            st.subheader("📋 Ablauf der Simulation")
            st.markdown(
                f"""
            1. **Stellen Sie jederzeit Fragen an {patient_forms.phrase("acc")}** – geben Sie diese im Chat ein.
            2. Wenn Sie genug Informationen gesammelt haben, führen Sie eine **körperliche Untersuchung** durch.
            3. Formulieren Sie Ihre **Differentialdiagnosen** und wählen Sie geeignete **diagnostische Maßnahmen**.
            4. Nach Erhalt der Befunde treffen Sie Ihre **endgültige Diagnose** und machen einen **Therapievorschlag**.
            5. Abschließend erhalten Sie ein **automatisches Feedback** zu Ihrem Vorgehen. Bei einigen, zufällig ausgewählten Simulationen wird das Feedback von ChatGPT fachlich unterstützt durch die
            <img src="{AMBOSS_LOGO_DATA_URI}" style="display:inline; width:80px; margin-left:8px; margin-bottom:-3px;"> -Wissensdatenbank.
            """,
                unsafe_allow_html=True,
            )

            # --- Teil 3: Zusätzliche Hinweise (Einklappbar) ---
            with st.expander("💡 Tipp für die Gesprächsführung", expanded=True):
                st.markdown(f"""
                Sie können {patient_forms.phrase("acc")} auch nach der ersten Diagnostik weiter befragen – z. B. bei neuen Verdachtsmomenten oder zur gezielten Klärung offener Fragen.
                """)

            # --- Teil 4: Warnhinweise (Als deutliche Warnung abgesetzt) ---
            st.warning("""
            **Wichtige Limitierungen:**
            * Überprüfen Sie alle Angaben und Hinweise der Kommunikation stets auf Richtigkeit.
            * Die Anwendung sollte aufgrund ihrer Limitationen nur unter ärztlicher Supervision genutzt werden.
            * Sie können bei Fragen und Unklarheiten den Chatverlauf in einer Text-Datei speichern.
            """, icon="⚠️")
            
            st.markdown("---")

    schreibe_instruktionen()

    if lade_callback and not st.session_state.instruktion_loader_fertig:
        with ladebereich:
            try:
                lade_callback()
            except Exception as exc:
                st.error("❌ Während der Vorbereitung ist ein Fehler aufgetreten. Bitte prüfen Sie die Debug-Hinweise im Kommentarbereich des Codes.")
                st.info("Tipp: Aktivieren Sie temporär zusätzliche st.write-Ausgaben im Lade-Callback, um den Fehler einzugrenzen.")
                st.info(f"Technische Details: {exc}")
            else:
                st.session_state.instruktion_loader_fertig = True
                schreibe_instruktionen()
                
    elif st.session_state.get("fall_vorbereitung_abgeschlossen"):
        with ladebereich:
            patient_name = st.session_state.get("patient_name", "").strip()
            if patient_name:
                start_hinweis = f"Fallvorbereitung abgeschlossen. Beginnen Sie das Gespräch mit {patient_name}."
            else:
                start_hinweis = "Fallvorbereitung abgeschlossen. Beginnen Sie das Gespräch mit der simulierten Patientin oder dem Patienten."
            st.success(f"✅ **{start_hinweis}**")
            
    elif not lade_callback:
        st.session_state.instruktion_loader_fertig = True

    if st.session_state.instruktion_loader_fertig:
        with fortsetzen_placeholder.container():
            st.markdown(
                """
                <style>
                    div[data-testid="stButton"] {
                        margin-top: 1.5rem;
                        display: flex;
                        justify-content: center;
                    }
                    div[data-testid="stButton"] > button {
                        background-color: #2e7d32;
                        border: 2px solid #1b5e20;
                        color: #ffffff;
                        font-weight: 700;
                        padding: 0.75rem 2.5rem;
                        border-radius: 999px;
                        box-shadow: 0 0 0 1px rgba(27, 94, 32, 0.35);
                    }
                    div[data-testid="stButton"] > button:hover {
                        background-color: #1b5e20;
                        border-color: #174f1b;
                        color: #ffffff;
                    }
                    div[data-testid="stButton"] > button:focus {
                        outline: 3px solid rgba(56, 142, 60, 0.45);
                        outline-offset: 2px;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Button Text hier angepasst
            button_gedrueckt = st.button("🚀 Simulation starten", key="start_ok_button", type="primary")

            if button_gedrueckt:
                st.switch_page("pages/1_Anamnese.py")

    st.stop()
