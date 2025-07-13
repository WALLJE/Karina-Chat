import streamlit as st
import os
import random
from PIL import Image


def show_sidebar():
    with st.sidebar:
        st.markdown("### Patientin")

        valid_images = []
        for f in os.listdir("pics"):
            if f.endswith(".png"):
                path = os.path.join("pics", f)
                try:
                    with Image.open(path) as img:
                        img.verify()
                    valid_images.append(path)
                except:
                    pass

        if "patient_logo" not in st.session_state and valid_images:
            st.session_state.patient_logo = random.choice(valid_images)

        try:
            st.image(st.session_state.patient_logo, width=160)
        except Exception as e:
            st.warning(f"⚠️ Bild konnte nicht geladen werden: {e}")

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
        if "diagnose_vorschlaege" in st.session_state:
            st.page_link("pages/5_Diagnose_und_Therapie.py", label="Diagnose und Therapie", icon="🧪")
    
        # Nur wenn finale Diagnose gesetzt
        if "diagnose_final" in st.session_state:
            st.page_link("Feedback_und_Download", label="📝 Feedback & Download")  

        st.markdown("---")
        st.caption("🔒 Seiten erscheinen automatisch, sobald Schritte abgeschlossen wurden.")

