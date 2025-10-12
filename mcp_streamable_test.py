import streamlit as st
import requests
import json

st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – JSON-RPC Beispiel")

# 🔑 Token aus Streamlit-Secrets laden
AMBOSS_KEY = st.secrets["Amboss_Token"]

# 🌐 MCP-Endpunkt (Streamable HTTP)
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

# 📚 Auswahl der verfügbaren Tools
TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie (EID nötig)": "get_drug_monograph",
    "Leitlinien abrufen (IDs nötig)": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media",
}

# 🔽 Tool auswählen
tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool_name = TOOLS[tool_label]

# ✍️ Freitext-Eingabe
query = st.text_input("🔍 Freitext (z. B. 'Mesalazin', 'Ileitis terminalis' oder eine EID/ID)")

# 🚀 Anfrage senden
if st.button("📤 Anfrage an AMBOSS senden"):
    # Argumente je nach Tooltyp
    arguments = {"language": "de"}

    if tool_name in ("search_article_sections", "search_pharma_substances", "search_media"):
        arguments["query"] = query
    elif tool_name == "get_definition":
        arguments["term"] = query
    elif tool_name == "get_drug_monograph":
        arguments["substance_eid"] = query  # benötigt EID
    elif tool_name == "get_guidelines":
        arguments["guideline_ids"] = [query]  # Liste erwartet

    # JSON-RPC-Payload
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    headers = {
        "Authorization": f"Bearer {AMBOSS_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    st.write("⏳ Anfrage wird gesendet...")

    # Anfrage an AMBOSS schicken
    response = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload), timeout=20)

    # 🔍 Antwort anzeigen (roh)
    try:
        data = response.json()
        st.success("✅ Antwort von AMBOSS erhalten:")
        st.json(data)  # Rohanzeige der MCP-Antwort
        amboss_result = data  # hier steht das JSON-Ergebnis als Variable bereit
    except Exception as e:
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(response.text)        # -> hier als Variable verfügbar:
        amboss_result = data["result"]        
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(response.text)
