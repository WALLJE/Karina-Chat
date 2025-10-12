import streamlit as st
import requests
import json

st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – Einfaches Beispiel")

# Token aus Streamlit-Secrets laden
AMBOSS_KEY = st.secrets["Amboss_Token"]

# MCP-Endpunkt (Streamable HTTP)
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

# Tools-Auswahl
TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie (EID nötig)": "get_drug_monograph",
    "Leitlinien abrufen (IDs nötig)": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media"
}

# Tool-Auswahlmenü
tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool = TOOLS[tool_label]

# Freitexteingabe
query = st.text_input("🔍 Freitext-Eingabe (z. B. 'Morbus Crohn' oder 'Mesalazin' oder eine EID)")

# Button zum Absenden
if st.button("📤 Anfrage an AMBOSS senden"):
    # Argumente je nach Tool
    args = {"language": "de"}
    if tool in ("search_article_sections", "search_pharma_substances", "search_media"):
        args["query"] = query
    elif tool == "get_definition":
        args["term"] = query
    elif tool == "get_drug_monograph":
        args["substance_eid"] = query  # normalerweise aus Suchergebnis
    elif tool == "get_guidelines":
        args["guideline_ids"] = [query]  # erwartet Liste

    # Payload für MCP
    payload = {
        "tool": tool,
        "args": args
    }

    # Header (mit akzeptiertem MIME-Typ)
    headers = {
        "Authorization": f"Bearer {AMBOSS_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    # Anfrage senden
    st.write("⏳ Anfrage wird gesendet...")
    response = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload), timeout=20)

    # Antwort anzeigen
    try:
        data = response.json()
        st.success("✅ Antwort von AMBOSS erhalten:")
        st.json(data)
        amboss_result = data  # in Variable speichern
    except Exception as e:
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(response.text)
