import streamlit as st

def zeige_instruktionen_vor_start():
    st.session_state.setdefault("instruktion_bestätigt", False)

    if not st.session_state.instruktion_bestätigt:
        st.markdown(f"""
#### Instruktionen für Studierende:
Sie übernehmen die Rolle einer Ärztin oder eines Arztes im Gespräch mit der virtuellen Patientin {st.session_state.patient_name}, die sich in Ihrer hausärztlichen Sprechstunde vorstellt. 
Ihr Ziel ist es, durch gezielte Anamnese und klinisches Denken eine Verdachtsdiagnose zu stellen sowie ein sinnvolles diagnostisches und therapeutisches Vorgehen zu entwickeln.

#### 🔍 Ablauf:

1. **Stellen Sie jederzeit Fragen an die Patientin** – geben Sie diese einfach im Chat ein.
2. Wenn Sie genug Informationen gesammelt haben, führen Sie eine **körperliche Untersuchung** durch.
3. Formulieren Sie Ihre **Differentialdiagnosen** und wählen Sie geeignete **diagnostische Maßnahmen**.
4. Nach Erhalt der Befunde treffen Sie Ihre **endgültige Diagnose** und machen einen **Therapievorschlag**.
5. Abschließend erhalten Sie ein **automatisches Feedback** zu Ihrem Vorgehen.

> 💬 **Hinweis:** Sie können die Patientin auch nach der ersten Diagnostik weiter befragen –  
z. B. bei neuen Verdachtsmomenten oder zur gezielten Klärung offener Fragen.

Im Wartezimmer sitzen weitere Patientinnen mit anderen Krankheitsbildern, die Sie durch einen erneuten Aufruf der App kennenlernen können.

---

⚠️ Bitte beachten Sie, dass Sie mit einem **KI-basierten, simulierten Patientinnenmodell** kommunizieren.
- Zur Qualitätssicherung werden Ihre Eingaben und die Reaktionen des ChatBots auf einem Server der Universität Halle gespeichert. Persönliche Daten (incl. E-Mail-Adresse oder IP-Adresse) werden nicht gespeichert, sofern Sie diese nicht selber angeben.
- Geben Sie daher **keine echten persönlichen Informationen** ein.
- **Überprüfen Sie alle Angaben und Hinweise der Kommunikation auf Richtigkeit.** 
- Die Anwendung sollte aufgrund ihrer Limitationen nur unter ärztlicher Supervision genutzt werden; Sie können bei Fragen und Unklarheiten den Chatverlauf in einer Text-Datei speichern.

---
""")
        st.page_link("pages/1_Anamnese.py", label="✅ Verstanden – weiter zur Anamnese")
        st.stop ()

