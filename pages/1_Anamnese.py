import streamlit as st
from openai import OpenAI, RateLimitError
import os
from datetime import datetime
from module.sidebar import show_sidebar
from module.navigation import redirect_to_start_page, render_next_page_link
from module.footer import copyright_footer
from module.offline import (
    display_offline_banner,
    get_offline_patient_reply,
    is_offline,
)
from module.loading_indicator import task_spinner
from module.supabase_content import SupabaseContentError
from module.token_counter import init_token_counters, add_usage
from module.gpt_timing import messe_gpt_aktion

copyright_footer()
show_sidebar()
display_offline_banner()

# Voraussetzungen prüfen
if "SYSTEM_PROMPT" not in st.session_state or "patient_name" not in st.session_state:
    redirect_to_start_page("⚠️ Der Fall ist noch nicht geladen. Bitte beginne über die Startseite.")

# OpenAI-Client initialisieren (nur wenn nicht bereits vorhanden)
if "openai_client" not in st.session_state:
    st.session_state["openai_client"] = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

client = st.session_state["openai_client"]

# Titel
st.subheader(f"Anamnese - {st.session_state.patient_name}")

# Startzeit setzen, falls noch nicht erfolgt
if "startzeit" not in st.session_state:
    st.session_state.startzeit = datetime.now()

# Nachrichtenverlauf initialisieren (außer system-Prompt)
if "messages" not in st.session_state:
    start_text = str(st.session_state.get("patient_begruessung", "")).strip()
    if not start_text:
        st.error("❌ Es ist kein Begrüßungssatz für das aktuelle Verhalten hinterlegt.")
        st.info(
            "Debug-Tipp: Bitte prüfe in Supabase, ob für das gewählte Verhalten ein Text in der Spalte 'verhalten_begrussung' eingetragen ist."
        )
        st.stop()

    st.session_state.messages = [
        {"role": "system", "content": st.session_state.SYSTEM_PROMPT},
        {"role": "assistant", "content": start_text},
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
    if is_offline():
        reply = get_offline_patient_reply(st.session_state.get("patient_name", ""))
        st.session_state.messages.append({"role": "assistant", "content": reply})
    else:
        ladeaufgaben = [
            "Übermittle Frage an das Sprachmodell",
            "Warte auf Antwortgenerierung",
            "Bereite Antwort für die Anzeige auf",
        ]
        with task_spinner(f"{st.session_state.patient_name} antwortet...", ladeaufgaben) as indikator:
            try:
                indikator.advance(1)
                # Vor jedem API-Kontakt stellen wir sicher, dass die Zähler existieren,
                # damit mehrere Chatsitzungen sauber kumuliert werden können.
                init_token_counters()
                # Für patientennahe, dialogische Antworten ist ein kleines,
                # natürlich klingendes Modell ausreichend und hält die Kosten
                # bei vielen Gesprächsrunden niedrig.
                response = messe_gpt_aktion(
                    lambda: client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.messages,
                        temperature=0.6,
                    ),
                    kontext="Anamnese-Chat",
                )
                # Die zurückgelieferten Token-Werte werden unmittelbar in die Session-Summen
                # übernommen. "total_tokens" enthält zwar bereits die Summe des aktuellen Calls,
                # dennoch addieren wir explizit, um über mehrere Gesprächsrunden hinweg eine
                # kumulierte Statistik führen zu können. Für Debugging kann hier bei Bedarf ein
                # st.write(...) aktiviert werden.
                add_usage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
                indikator.advance(1)
                reply = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": reply})
                indikator.advance(1)
            except RateLimitError:
                st.error("🚫 Die Anfrage konnte nicht verarbeitet werden, da die OpenAI-API derzeit überlastet ist. Bitte versuchen Sie es in einigen Minuten erneut.")
    st.rerun()

# Abschlussoption anzeigen
# st.markdown("---")
# if st.button("✅ Anamnese abgeschlossen"):
#    st.session_state.anamnese_done = True
#    st.success("Anamnese wurde als abgeschlossen markiert.")

# Weiter-Link zur Diagnostik
# Hinweis: "href='/Diagnostik'" sorgt für internen Seitenwechsel, nicht für neues Fenster

render_next_page_link(
    "pages/2_Koerperliche_Untersuchung.py",
    label="Weiter zur Körperlichen Untersuchung",
    icon="🩺",
)
