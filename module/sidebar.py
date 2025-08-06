reimport streamlit as st
import os
import random
from PIL import Image


def show_sidebar():
    # DEBUG
    # st.sidebar.write("🧪 DEBUG: keys in session_state:", list(st.session_state.keys()))

    with st.sidebar:
        # st.markdown("### Patientin")

        # Standardverzeichnis
        pic_dir = "pics"
        
        # Wenn Alter verfügbar und > 40: Senior-Verzeichnis verwenden
        if "patient_age" in st.session_state:
            try:
                if int(st.session_state["patient_age"]) > 40:
                    pic_dir = os.path.join("pics", "senior")
            except:
                pass  # falls Alter nicht korrekt als Zahl eingegeben wurde
        
        valid_images = []
        if os.path.isdir(pic_dir):
            for f in os.listdir(pic_dir):
                if f.endswith(".png"):
                    path = os.path.join(pic_dir, f)
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
            st.page_link("pages/6_Feedback_und_Evaluation.py", label="📝 Feedback & Download")  

        st.markdown("---")
        st.caption("🔒 Weitere Seiten erscheinen automatisch, sobald diagnostische Schritte abgeschlossen wurden.")

