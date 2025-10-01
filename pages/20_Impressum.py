import streamlit as st
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.patient_language import get_patient_forms

copyright_footer()
show_sidebar()

def show_impressum():
    patient_forms = get_patient_forms()
    st.markdown(f"""
    ## Impressum
    
    **Projektleitung**  
    Jens Walldorf  
    Universitätsklinikum Halle (Saale)  
    Klinik für Innere Medizin I – Gastroenterologie  
    Ernst-Grube-Straße 40
    06120 Halle
     
    E-Mail: jens.walldorf@uk-halle.de  

    ---
    ⚠️ Bitte beachten Sie, dass Sie mit einem **experimentellen, KI-basierten, simulierten {patient_forms.compound("modell")}** kommunizieren, welches **ausschließlich zu Lehrzwecken** konzipiert ist.
    
    Wichtiges Lernziel bei der Verwendung der App ist es unter anderem, die Limitationen (**Fehlinterpretationen, falsche Informationen**) in den von der KI generierten Antworten zu identifizieren.
    
    ⚠️ Die von der KI generierten Informationen aus dieser App können fehlerhaft sein! Alle Informationen, die von der KI mitgeteilt werden, müssen mit geeigneter Fachliteratur abgeglichen werden bzw. können Diskussiongrundlage im Studentenunterricht sein.
    
    - Zur Qualitätssicherung werden Ihre Eingaben und die Reaktionen des ChatBots auf einem Server der Universität Halle gespeichert. Persönliche Daten (incl. E-Mail-Adresse oder IP-Adresse) werden nicht gespeichert, sofern Sie diese nicht selber angeben.
    - Geben Sie daher **keine echten persönlichen Informationen** ein.
    - **Überprüfen Sie alle Angaben und Hinweise der Kommunikation auf Richtigkeit.** 
    - Die Anwendung sollte aufgrund ihrer Limitationen nur unter ärztlicher Supervision genutzt werden; Sie können bei Fragen und Unklarheiten den Chatverlauf in einer Text-Datei speichern.

    Für die Richtigkeit der Inhalte kann entsprechend keine Haftung übernommen werden.

    ---
    
    
    Stand: August 2025
    """)

show_impressum()
