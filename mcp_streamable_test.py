import streamlit as st
import requests
import json

# --- Seitenkonfiguration ---
st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")

st.title("💊 AMBOSS MCP – Einfaches Beispiel")

# --- Token aus Streamlit Secrets laden ---
AMBOSS_KEY = st.secrets["Amboss_Token"]

# --- Basis-URL für Streamable HTTP (nicht SSE!) ---
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

# --- Liste der verfügbaren Tools (Auswahlmenü) ---
TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie": "get_drug_monograph",
    "Leitlinien abrufen": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media"
}

# --- Tool-Auswahl ---
tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool = TOOLS[tool_label]

# --- Freitexteingabe ---
query = st.text_input("🔍 Freitext-Eingabe (z. B. 'Morbus Crohn' oder 'Mesalazin')")

# --- Button zum Absenden ---
if st.button("📤 Anfrage an AMBOSS senden"):
    # JSON-Payload für MCP-Aufruf
    payload = {
        "tool": tool,
        "args": {
            "query": query,
            "language": "de"
        }
    }

    # HTTP-POST-Request an den MCP-Endpunkt
    headers = {
        "Authorization": f"Bearer {AMBOSS_KEY}",
        "Content-Type": "application/json"
    }

    st.write("⏳ Anfrage wird gesendet...")
    response = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload))

    # Antwort als JSON interpretieren
    try:
        data = response.json()
        st.success("✅ Antwort von AMBOSS erhalten:")
        st.json(data)  # zur Anzeige der Rohdaten
        # Du kannst den Rückgabewert auch in einer Variable speichern:
        amboss_result = data
    except Exception as e:
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(response.text)
