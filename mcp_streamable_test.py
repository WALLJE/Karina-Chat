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
# 🔧 Hilfsfunktionen
# -----------------------------------------------------------
def try_parse_embedded_json_text(content_item_text: str):
    """
    Einige AMBOSS-Antworten liefern in content[0].text einen JSON-String.
    Den versuchen wir hier zusätzlich zu parsen und zurückzugeben.
    Scheitert das, geben wir None zurück.
    """
    try:
        return json.loads(content_item_text)
    except Exception:
        return None

def truncate(s: str, n: int = 500) -> str:
    s = s or ""
    return (s[:n] + " …") if len(s) > n else s

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
        arguments["substance_eid"] = query  # benötigt EID (in der Praxis über Suchtool holen)
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

    if "error" in data:
        st.error(f"❌ AMBOSS-Fehler: {data['error'].get('message')}")
        if "code" in data["error"]:
            st.write(f"Fehlercode: {data['error']['code']}")
        if "data" in data["error"]:
            st.json(data["error"]["data"])
        st.stop()

    result = data.get("result", {})

    # 1) Standardfall: result["results"] (z. B. für einfache Suchen)
    if isinstance(result, dict) and "results" in result:
        st.markdown("### Ergebnisse")
        for item in result["results"]:
            # Versuche typische Felder
            title = item.get("title") or item.get("article_title") or item.get("name") or "–"
            snippet = item.get("snippet") or item.get("chunk") or ""
            url = item.get("url")
            article_id = item.get("article_id") or item.get("eid") or item.get("id")

            st.markdown(f"**{title}**")
            if snippet:
                st.markdown(truncate(snippet, 800))
            if url:
                st.markdown(f"🔗 [Link]({url})")
            if article_id:
                st.caption(f"EID/ID: {article_id}")
            st.markdown("---")

    # 2) Sonderfall: result["content"] enthält eine Liste von Segmenten,
    #    wobei content[0].text selbst ein JSON-String ist (eingebettetes JSON)
    elif isinstance(result, dict) and "content" in result:
        content = result["content"]

        # Direkte Textdarstellung, falls nichts eingebettet ist
        if isinstance(content, str):
            st.markdown("### Inhalt (Text)")
            st.write(content)
        elif isinstance(content, list):
            # Erstes text-Segment inspizieren
            parsed_any = False
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text" and isinstance(seg.get("text"), str):
                    embedded = try_parse_embedded_json_text(seg["text"])
                    if embedded:
                        parsed_any = True
                        # Erwartetes Schema: embedded["results"] mit chunk/url/article_id
                        results = embedded.get("results") or embedded.get("data") or []
                        st.markdown("### Extrahierte Ergebnisse aus eingebettetem JSON")
                        if isinstance(results, list) and results:
                            for item in results:
                                title = item.get("title") or item.get("article_title") or "–"
                                snippet = item.get("snippet") or item.get("chunk") or ""
                                url = item.get("url")
                                article_id = item.get("article_id") or item.get("eid") or item.get("id")

                                st.markdown(f"**{title}**")
                                if snippet:
                                    st.markdown(truncate(snippet, 800))
                                if url:
                                    st.markdown(f"🔗 [Link]({url})")
                                if article_id:
                                    st.caption(f"EID/ID: {article_id}")
                                st.markdown("---")
                        else:
                            st.info("Kein 'results'-Array im eingebetteten JSON gefunden – zeige komplettes eingebettetes Objekt:")
                            st.json(embedded)
                # Falls segment kein parsebares JSON enthält, zeige den Text einfach an
            if not parsed_any:
                st.markdown("### Inhalt (Segmente)")
                for seg in content:
                    if isinstance(seg, dict) and seg.get("type") == "text":
                        st.markdown(truncate(seg.get("text") or "", 1200))
                        st.markdown("---")
                    else:
                        st.json(seg)

        else:
            st.info("Unbekanntes 'content'-Format – zeige alles an:")
            st.json(content)

    # 3) Sonst: wir kennen das Schema nicht → alles ausgeben
    else:
        st.info("Keine standardisierten Felder erkannt – gesamte 'result'-Struktur:")
        st.json(result)

    # 👉 Ergebnis als Variable verfügbar (falls du es weiterverwenden willst)
    amboss_result = data
