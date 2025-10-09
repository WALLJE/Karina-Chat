import streamlit as st
from datetime import datetime
from module.sidebar import show_sidebar
from module.footer import copyright_footer
from module.offline import (
    display_offline_banner,
    get_offline_patient_reply,
    is_offline,
)
from module.llm_state import (
    ConfigurationError,
    MCPClientError,
    RateLimitError,
    ensure_llm_client,
    get_provider_label,
)

copyright_footer()
show_sidebar()
display_offline_banner()

# Voraussetzungen prüfen
if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
    st.warning("⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite.")
    st.page_link("Karina_Chat_2.py", label="⬅ Zur Startseite")
    st.stop()

# LLM-Client initialisieren (Fallback, falls Seite direkt geöffnet wurde)
if "mcp_client" not in st.session_state and not is_offline():
    try:
        ensure_llm_client()
    except ConfigurationError as exc:
        st.warning(
            "⚙️ Die Konfiguration für {provider} ist unvollständig."
            " Die Seite wechselt in den Offline-Modus.\n\n"
            f"Details: {exc}".format(provider=get_provider_label())
        )
        st.session_state["offline_mode"] = True
        st.session_state["mcp_client"] = None
    except MCPClientError as exc:
        st.error(
            "❌ Der LLM-Client konnte nicht initialisiert werden. Bitte prüfe die "
            "aktuellen Zugangsdaten oder die Netzwerkverbindung.\n\n"
            f"Fehlerdetails: {exc}"
        )
        st.stop()

client = st.session_state.get("mcp_client")

# Titel
st.subheader(f"Anamnese - {st.session_state.patient_name}")

# Startzeit setzen, falls noch nicht erfolgt
if "startzeit" not in st.session_state:
    st.session_state.startzeit = datetime.now()

# Nachrichtenverlauf initialisieren (außer system-Prompt)
if "messages" not in st.session_state:
    start_text = "Guten Tag, ich bin froh, dass ich mich heute bei Ihnen vorstellen kann."
    st.session_state.messages = [
        {"role": "system", "content": st.session_state.SYSTEM_PROMPT},
        {"role": "assistant", "content": start_text}
    ]

# Nachrichtenverlauf anzeigen (ohne System-Prompt)
for msg in st.session_state.messages[1:]:
    sender = st.session_state.patient_name if msg["role"] == "assistant" else "Du"
    st.markdown(f"**{sender}:** {msg['content']}")

# Eingabeformular
with st.form(key="eingabe_formular", clear_on_submit=True):
    user_input = st.text_input(f"Deine Frage an {st.session_state.patient_name}:")
    submit_button = st.form_submit_button(label="Absenden")

if submit_button and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    if is_offline() or client is None:
        reply = get_offline_patient_reply(st.session_state.get("patient_name", ""))
        st.session_state.messages.append({"role": "assistant", "content": reply})
    else:
        with st.spinner(f"{st.session_state.patient_name} antwortet..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=st.session_state.messages,
                    temperature=0.6
                )
                reply = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except RateLimitError:
                st.error(
                    "🚫 Die Anfrage konnte nicht verarbeitet werden, weil der LLM-Dienst aktuell ausgelastet ist."
                    " Bitte versuche es in einigen Minuten erneut."
                )
    st.rerun()

# Abschlussoption anzeigen
# st.markdown("---")
# if st.button("✅ Anamnese abgeschlossen"):
#    st.session_state.anamnese_done = True
#    st.success("Anamnese wurde als abgeschlossen markiert.")

# Weiter-Link zur Diagnostik
# Hinweis: "href='/Diagnostik'" sorgt für internen Seitenwechsel, nicht für neues Fenster

st.page_link("pages/2_Koerperliche_Untersuchung.py", label="🩺 Weiter zur Körperlichen Untersuchung", icon=None)
