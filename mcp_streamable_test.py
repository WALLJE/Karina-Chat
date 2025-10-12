import streamlit as st
import requests
import json

st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – JSON-RPC Beispiel")

AMBOSS_KEY = st.secrets["Amboss_Token"]
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie (EID nötig)": "get_drug_monograph",
    "Leitlinien abrufen (IDs nötig)": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media",
}

tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool_name = TOOLS[tool_label]

query = st.text_input("🔍 Freitext (z. B. 'Mesalazin', 'Ileitis terminalis' oder eine EID/ID)")

if st.button("📤 Anfrage an AMBOSS senden"):
    # Arguments je nach Tool bauen
    arguments = {"language": "de"}

    if tool_name in ("search_article_sections", "search_pharma_substances", "search_media"):
        arguments["query"] = query
    elif tool_name == "get_definition":
        arguments["term"] = query
    elif tool_name == "get_drug_monograph":
        # erwartet eine substance EID (vorher über search_* ermitteln)
        arguments["substance_eid"] = query
    elif tool_name == "get_guidelines":
        # erwartet i. d. R. eine Liste von IDs/EIDs
        arguments["guideline_ids"] = [query]

    # JSON-RPC 2.0 Payload
    payload = {
        "jsonrpc": "2.0",
        "id": "1",  # beliebige Korrelation; String oder Zahl
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
    resp = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload), timeout=20)

    # Ergebnis parsen: JSON-RPC → result / error
    data = resp.json()
    if "error" in data:
        st.error(f"❌ AMBOSS-Fehler: {data['error'].get('message')}")
        st.json(data)
    else:
        st.success("✅ Antwort von AMBOSS erhalten:")
        st.json(data)  # Rohanzeige
        # -> hier als Variable verfügbar:
        amboss_result = data["result"]        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(response.text)
