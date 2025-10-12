import streamlit as st
import requests
import json

# -----------------------------------------------------------
# 🧩 Grundkonfiguration
# -----------------------------------------------------------
st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – JSON-RPC Beispiel mit Formatierung")

# 🔑 Token aus Streamlit-Secrets laden
AMBOSS_KEY = st.secrets["Amboss_Token"]

# 🌐 MCP-Endpunkt (Streamable HTTP)
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

# 📚 Liste der verfügbaren Tools
TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie (EID nötig)": "get_drug_monograph",
    "Leitlinien abrufen (IDs nötig)": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media",
}

# -----------------------------------------------------------
# 🧭 Benutzeroberfläche
# -----------------------------------------------------------
tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool_name = TOOLS[tool_label]

query = st.text_input("🔍 Freitext (z. B. 'Mesalazin', 'Ileitis terminalis' oder eine EID/ID)")

# -----------------------------------------------------------
# 🚀 Anfrage senden
# -----------------------------------------------------------
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
        arguments["guideline_ids"] = [query]  # erwartet Liste

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

    st.write("⏳ Anfrage wird gesendet ...")

    # HTTP-POST an den MCP-Server
    response = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload), timeout=30)

    # -------------------------------------------------------
    # 🔍 Antwort parsen: JSON oder SSE
    # -------------------------------------------------------
    content_type = response.headers.get("Content-Type", "")
    body = response.text

    try:
        if "application/json" in content_type:
            data = response.json()
        else:
            # Server-Sent-Events: Zeilen nach "data:" extrahieren
            json_chunks = []
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    json_chunks.append(line[len("data:"):].strip())
            data = json.loads("".join(json_chunks))
    except Exception as e:
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(body)
        st.stop()

    # -------------------------------------------------------
    # 🧾 Rohanzeige
    # -------------------------------------------------------
    st.success("✅ Antwort von AMBOSS erhalten (Rohdaten):")
    st.json(data)

    # -------------------------------------------------------
    # 🧮 Aufbereitete Darstellung
    # -------------------------------------------------------
    st.markdown("---")
    st.subheader("📘 Aufbereitete Antwort")

    # JSON-RPC unterscheidet zwischen 'result' und 'error'
    if "error" in data:
        st.error(f"❌ AMBOSS-Fehler: {data['error'].get('message')}")
        if "code" in data["error"]:
            st.write(f"Fehlercode: {data['error']['code']}")
        if "data" in data["error"]:
            st.json(data["error"]["data"])
    else:
        result = data.get("result", {})
        # Das eigentliche Ergebnis liegt meist in result["content"] oder result["results"]
        if "results" in result:
            st.markdown("### Ergebnisse")
            for item in result["results"]:
                title = item.get("title") or item.get("article_title") or "–"
                snippet = item.get("snippet") or ""
                st.markdown(f"**{title}**  \n{snippet}")
                st.markdown("---")
        elif "content" in result:
            st.markdown("### Inhalt")
            st.write(result["content"])
        else:
            st.info("Keine standardisierten Felder gefunden – gesamte Antwort:")
            st.json(result)

    # 👉 Ergebnis als Variable verfügbar
    amboss_result = data
