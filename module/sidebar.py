import os
import random
from pathlib import Path

import streamlit as st
from PIL import Image


# Der Logo-Pfad wird zentral definiert, damit bei einem ersten Seitenaufruf
# bewusst immer dasselbe Bild erscheint. So sehen Nutzerinnen und Nutzer sofort
# das Klinik-Branding, wenn noch kein patientenspezifisches Foto zugeordnet
# werden konnte.
STANDARD_LOGO_PFAD = Path(__file__).resolve().parents[1] / "pics" / "Logo_Klinik.png"

# Die Zielbreite für das Sidebar-Bild wird etwas großzügiger gewählt, damit das
# Klinik-Logo und spätere Patientenbilder den vorhandenen Platz besser nutzen
# und in der Sidebar klar erkennbar sind. Über den einstellbaren Wert kann das
# Erscheinungsbild bei Bedarf schnell angepasst werden, ohne die Logik weiter
# zu verändern.
SIDEBAR_BILD_BREITE = 220


def show_sidebar():
    # DEBUG
    # st.sidebar.write("🧪 DEBUG: keys in session_state:", list(st.session_state.keys()))

    with st.sidebar:
        # st.markdown("### Patientin")

        def bestimme_bilder_ordner():
            """
            Liefert den Pfad zu einem alters- und geschlechtsspezifischen Unterordner.
            
            Ist noch kein Geschlecht/Alter gesetzt (z. B. direkt nach dem Start),
            wird ``None`` zurückgegeben, damit kein zufälliges Bild ausgewählt wird
            und das Klinik-Logo sichtbar bleibt.
            """
            geschlecht = str(st.session_state.get("patient_gender", "")).strip().lower()
            try:
                alter = int(st.session_state.get("patient_age", ""))
            except (TypeError, ValueError):
                alter = None

            if alter is None or geschlecht not in {"m", "w"}:
                return None

            if geschlecht == "w":
                if alter <= 30:
                    unterordner = "junior_female"
                elif alter <= 47:
                    unterordner = "mid_female"
                else:
                    unterordner = "senior_female"
            else:  # männlich
                if alter <= 30:
                    unterordner = "junior_male"
                elif alter <= 47:
                    unterordner = "mid_male"
                else:
                    unterordner = "senior_male"

            return os.path.join("pics", unterordner)

        def lade_gueltige_bilder(ordnerpfad):
            """
            Lädt nur valide PNG-Dateien aus dem gewünschten Ordner und filtert das
            Klinik-Logo bewusst heraus, damit dieses niemals zufällig als Patienten-
            bild ausgewählt wird.
            """
            bilder = []
            if ordnerpfad and os.path.isdir(ordnerpfad):
                for eintrag in os.listdir(ordnerpfad):
                    if eintrag.lower().endswith(".png"):
                        pfad = os.path.join(ordnerpfad, eintrag)
                        # Logo explizit überspringen, damit es nur als definierter
                        # Startplatzhalter eingesetzt wird.
                        if Path(pfad).name == STANDARD_LOGO_PFAD.name:
                            continue
                        try:
                            with Image.open(pfad) as img:
                                img.verify()
                            bilder.append(pfad)
                        except Exception:
                            continue
            return bilder

        pic_dir = bestimme_bilder_ordner()
        valid_images = lade_gueltige_bilder(pic_dir)

        if "patient_logo" not in st.session_state:
            # Beim allerersten Aufruf setzen wir das Klinik-Logo als Platzhalter,
            # damit kein zufälliges Bild erscheint und der Start klar erkennbar ist.
            # Falls das Logo fehlen sollte, kann per Debugging-Hinweis
            # ``st.sidebar.write(STANDARD_LOGO_PFAD)`` aktiviert werden, um den
            # erwarteten Pfad zu prüfen.
            if STANDARD_LOGO_PFAD.is_file():
                st.session_state.patient_logo = str(STANDARD_LOGO_PFAD)
        
        if valid_images:
            # Sobald valide patientenspezifische Bilder vorhanden sind, ersetzen
            # wir den Platzhalter, damit ein zum Szenario passendes Foto erscheint.
            # Der Austausch erfolgt auch, wenn der bisherige Pfad nicht mehr im
            # aktuellen Pool enthalten ist (z. B. nach einem Szenariowechsel).
            if (
                "patient_logo" not in st.session_state
                or st.session_state.patient_logo == str(STANDARD_LOGO_PFAD)
                or st.session_state.patient_logo not in valid_images
            ):
                st.session_state.patient_logo = random.choice(valid_images)

        # Ein leerer Platzhalter sorgt dafür, dass die Sidebar nicht springt, wenn noch kein Bild gesetzt ist.
        bildplatzhalter = st.empty()

        patientenbild = st.session_state.get("patient_logo")

        if patientenbild:
            try:
                # Hinweis für Debugging: Bei Bedarf kann die folgende Zeile aktiviert werden,
                # um den aktuell verwendeten Bildpfad in der Sidebar auszugeben.
                # st.sidebar.write("🧪 DEBUG: Verwendeter Bildpfad:", patientenbild)
                # Die Bildbreite orientiert sich an `SIDEBAR_BILD_BREITE`, damit das Logo größer
                # erscheint und die Sidebar optisch ausfüllt. Bei Änderungen an der Sidebar-Breite
                # kann der Wert unkompliziert angepasst werden.
                bildplatzhalter.image(
                    patientenbild,
                    width=SIDEBAR_BILD_BREITE,
                )
            except Exception as e:
                st.warning(f"⚠️ Bild konnte nicht geladen werden: {e}")
        else:
            # Sichtbarer, aber neutraler Platzhalter, damit die Bildfläche reserviert bleibt.
            bildplatzhalter.markdown(
                """
                <div style="width: 100%; max-width: 240px; height: 160px; border-radius: 12px; background-color: rgba(0, 0, 0, 0.05);"></div>
                """,
                unsafe_allow_html=True,
            )

        if all(k in st.session_state for k in ["patient_name", "patient_age"]):
            patient_text = f"**{st.session_state.patient_name} ({st.session_state.patient_age})**"
            if "patient_job" in st.session_state:
                patient_text += f", {st.session_state.patient_job}"
            st.markdown(patient_text)

        st.markdown("### Navigation")
        st.page_link("pages/1_Anamnese.py", label="Anamnese", icon="💬")

# Nur wenn mind. eine Frage gestellt wurde (Chatverlauf existiert)
        if "messages" in st.session_state and any(m["role"] == "user" for m in st.session_state["messages"]):
            st.page_link("pages/2_Koerperliche_Untersuchung.py", label="Untersuchung", icon="🩺")
    
        # Nur wenn Untersuchung erfolgt ist
        if "koerper_befund" in st.session_state:
            st.page_link("pages/4_Diagnostik_und_Befunde.py", label="Diagnostik", icon="🧪")
    
        # Nur wenn Diagnostik abgeschlossen (Verdachtsdiagnosen vorliegen)
        if (
            "user_diagnostics" in st.session_state and
            "user_ddx2" in st.session_state
        ):
            st.page_link("pages/5_Diagnose_und_Therapie.py", label="Diagnose und Therapie", icon="💊")
    
        # Nur wenn finale Diagnose gesetzt
        if (
            "final_diagnose" in st.session_state and
            "therapie_vorschlag" in st.session_state
        ):
            st.page_link("pages/6_Feedback.py", label="📝 Feedback")

        if st.session_state.get("final_feedback"):
            st.page_link("pages/7_Evaluation_und_Download.py", label="📊 Evaluation")

        st.page_link("pages/20_Impressum.py", label="Impressum und Hinweise", icon="📰")

        if st.session_state.get("is_admin"):
            st.page_link("pages/21_Admin.py", label="🔑 Adminbereich")

        st.markdown("---")

