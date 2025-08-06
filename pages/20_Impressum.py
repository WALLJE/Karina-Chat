import streamlit as st

def show_impressum():
    st.title("Impressum")
    
    st.markdown("""
    ## Impressum
    
    **Projektleitung**  
    Jens Walldorf  
    Universitätsklinikum Halle (Saale)  
    Klinik für Innere Medizin I – Gastroenterologie  
    Ernst-Grube-Straße 40
    06120 Halle
     
    E-Mail: jens.walldorf@uk-halle.de  

    ---
    
    Es handelt sich bei diesen Seiten um ein experimentelles Patientenmodell ausschließlich zu Lehrzwecken. Wichtiges Lernziel der App ist es unter anderem, die Limitationen (Fehlinterpretationen, falsche Informationen) in der von der KI generierten Antworten zu identifizieren.
    ⚠️ Die von der KI generierten Informationen aus dieser App können fehlerhaft sein! Alle Informationen, die von der KI mitgeteilt werden, müssen mit geeigneter Fachliteratur abgeglichen werden bzw. können Diskussiongrundlage im Studentenunterricht sein.
    
    ⚠️ Bitte beachten Sie daher, dass Sie mit einem **KI-basierten, simulierten Patientinnenmodell** kommunizieren.
    - Zur Qualitätssicherung werden Ihre Eingaben und die Reaktionen des ChatBots auf einem Server der Universität Halle gespeichert. Persönliche Daten (incl. E-Mail-Adresse oder IP-Adresse) werden nicht gespeichert, sofern Sie diese nicht selber angeben.
    - Geben Sie daher **keine echten persönlichen Informationen** ein.
    - **Überprüfen Sie alle Angaben und Hinweise der Kommunikation auf Richtigkeit.** 
    - Die Anwendung sollte aufgrund ihrer Limitationen nur unter ärztlicher Supervision genutzt werden; Sie können bei Fragen und Unklarheiten den Chatverlauf in einer Text-Datei speichern.

    Für die Richtigkeit der Inhalte kann entsprechend auch keine Haftung übernommen werden.

    ---
    
    
    Stand: August 2025
    """)

show_impressum()
