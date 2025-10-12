import streamlit as st
import requests
import json
import re
from typing import Optional

# -----------------------------------------------------------
# Grundkonfiguration
# -----------------------------------------------------------
st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – JSON-RPC Beispiel mit Formatierung + Kopier-Ansicht")

# Token aus Streamlit-Secrets laden
AMBOSS_KEY = st.secrets["Amboss_Token"]

# MCP-Endpunkt (Streamable HTTP)
AMBOSS_URL = "https://content-mcp.de.production.amboss.com/mcp"

# Liste der verfügbaren Tools
TOOLS = {
    "Artikelabschnitte suchen": "search_article_sections",
    "Arzneistoff suchen": "search_pharma_substances",
    "Arzneimittel-Monographie (EID nötig)": "get_drug_monograph",
    "Leitlinien abrufen (IDs nötig)": "get_guidelines",
    "Begriff definieren": "get_definition",
    "Medien suchen": "search_media",
}

# -----------------------------------------------------------
# Hilfsfunktionen
# -----------------------------------------------------------
def fix_mojibake(s: str) -> str:
    """Repariert typische UTF-8/Latin-1-Mojibake (Ã¼, Ã¤, â€“, Â, …)."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        for a, b in (
            ("â€“", "–"),
            ("â€”", "—"),
            ("â€ž", "„"),
            ("â€œ", "“"),
            ("â€˜", "‚"),
            ("â€™", "’"),
            ("â€¡", "‡"),
            ("â€¢", "•"),
            ("Â", ""),
        ):
            s = s.replace(a, b)
        return s


def clean_placeholders(text: str, url: Optional[str] = None) -> str:
    """
    Wandelt AMBOSS-Platzhalter in nutzbares Markdown/HTML um:
    - {NewLine} -> <br>
    - {Sub}/{/Sub} -> <sub>...</sub>
    - {Sup}/{/Sup} -> <sup>...</sup>
    - {RefNote:ID} -> [†](url) (ein Symbol-Link)
    - übrige {Ref...} entfernen
    """
    if not isinstance(text, str):
        return text

    t = fix_mojibake(text)
    t = t.replace("{Sub}", "<sub>").replace("{/Sub}", "</sub>")
    t = t.replace("{Sup}", "<sup>").replace("{/Sup}", "</sup>")
    t = t.replace("{NewLine}", "<br>")

    # {RefNote:...} → †-Link (wenn URL vorhanden)
    if url:
        t = re.sub(r"\{RefNote:[^}]+\}", f"[†]({url})", t)
    else:
        t = re.sub(r"\{RefNote:[^}]+\}", "†", t)

    # übrige {Ref...} entfernen (stört Tabellen)
    t = re.sub(r"\{Ref[^\}]+\}", "", t)

    # überflüssige Leerzeichen glätten
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t


def try_parse_embedded_json_text(content_item_text: str):
    """
    Einige Antworten liefern in content[*].text einen JSON-String.
    Diesen versuchen wir zusätzlich zu parsen.
    """
    if not isinstance(content_item_text, str):
        return None
    candidate = fix_mojibake(content_item_text)
    try:
        return json.loads(candidate)
    except Exception:
        return None


def truncate(s: str, n: int = 800) -> str:
    s = s or ""
    return (s[:n] + " …") if len(s) > n else s


# -----------------------------------------------------------
# Benutzeroberfläche
# -----------------------------------------------------------
tool_label = st.selectbox(
    "Welches AMBOSS-Tool möchtest du verwenden?",
    list(TOOLS.keys())
)
tool_name = TOOLS[tool_label]

query = st.text_input(
    "🔍 Freitext (z. B. 'Mesalazin', 'Ileitis terminalis' oder eine EID/ID)"
)

# -----------------------------------------------------------
# Anfrage senden
# -----------------------------------------------------------
if st.button("📤 Anfrage an AMBOSS senden"):
    # Argumente je nach Tooltyp
    arguments = {"language": "de"}

    if tool_name in ("search_article_sections", "search_pharma_substances", "search_media"):
        arguments["query"] = query
    elif tool_name == "get_definition":
        arguments["term"] = query
    elif tool_name == "get_drug_monograph":
        arguments["substance_eid"] = query  # benötigt EID (i. d. R. zuvor via search_* ermitteln)
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
    response = requests.post(
        AMBOSS_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=30
    )

    # -------------------------------------------------------
    # Antwort parsen: JSON oder SSE
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
    # Rohdaten: copy-friendly + Download
    # -------------------------------------------------------
    st.success("✅ Antwort von AMBOSS erhalten (Rohdaten):")
    raw_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.code(raw_str, language="json")
    st.download_button(
        "⬇️ Rohantwort als JSON speichern",
        data=raw_str.encode("utf-8"),
        file_name="amboss_mcp_raw.json",
        mime="application/json"
    )

    # -------------------------------------------------------
    # Aufbereitete Darstellung → als Markdown sammeln
    # -------------------------------------------------------
    pretty_blocks = []

    if "error" in data:
        msg = data["error"].get("message", "Unbekannter Fehler")
        code = data["error"].get("code")
        block = f"**Fehler:** {msg}" + (f" (Code {code})" if code is not None else "")
        pretty_blocks.append(block)
    else:
        result = data.get("result", {})

        # 1) results-Liste (Suchergebnisse u. ä.)
        if isinstance(result, dict) and "results" in result:
            items = result["results"] or []
            if items:
                pretty_blocks.append("### Ergebnisse")
            for item in items:
                title = item.get("title") or item.get("article_title") or item.get("name") or "–"
                snippet = item.get("snippet") or item.get("chunk") or ""
                url = item.get("url")
                article_id = item.get("article_id") or item.get("eid") or item.get("id")
                pretty = clean_placeholders(snippet, url)
                block = f"**{fix_mojibake(title)}**\n\n{pretty}"
                if url:
                    block += f"\n\n🔗 {url}"
                if article_id:
                    block += f"\n\n_EID/ID: {article_id}_"
                pretty_blocks.append(block)

        # 2) content-Liste (Segmente / eingebettetes JSON)
        elif isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, str):
                pretty_blocks.append("### Inhalt (Text)")
                pretty_blocks.append(clean_placeholders(content))
            elif isinstance(content, list):
                parsed_any = False
                embedded_blocks = []
                for seg in content:
                    if isinstance(seg, dict) and seg.get("type") == "text" and isinstance(seg.get("text"), str):
                        embedded = try_parse_embedded_json_text(seg["text"])
                        if embedded:
                            parsed_any = True
                            results = embedded.get("results") or embedded.get("data") or []
                            if isinstance(results, list) and results:
                                for item in results:
                                    title = item.get("title") or item.get("article_title") or "–"
                                    snippet = item.get("snippet") or item.get("chunk") or ""
                                    url = item.get("url")
                                    article_id = item.get("article_id") or item.get("eid") or item.get("id")
                                    pretty = clean_placeholders(snippet, url)
                                    block = f"**{fix_mojibake(title)}**\n\n{pretty}"
                                    if url:
                                        block += f"\n\n🔗 {url}"
                                    if article_id:
                                        block += f"\n\n_EID/ID: {article_id}_"
                                    embedded_blocks.append(block)
                            else:
                                embedded_blocks.append(
                                    "```json\n" + json.dumps(embedded, ensure_ascii=False, indent=2) + "\n```"
                                )
                if parsed_any and embedded_blocks:
                    pretty_blocks.append("### Extrahierte Ergebnisse (eingebettetes JSON)")
                    pretty_blocks.extend(embedded_blocks)
                else:
                    # Fallback: rohe Segmente, aber bereinigt
                    pretty_blocks.append("### Inhalt (Segmente)")
                    for seg in content:
                        if isinstance(seg, dict) and seg.get("type") == "text":
                            pretty_blocks.append(clean_placeholders(seg.get("text") or ""))
                        else:
                            pretty_blocks.append(
                                "```json\n" + json.dumps(seg, ensure_ascii=False, indent=2) + "\n```"
                            )
            else:
                pretty_blocks.append(
                    "Unbekanntes 'content'-Format:\n\n```json\n" +
                    json.dumps(content, ensure_ascii=False, indent=2) +
                    "\n```"
                )
        else:
            pretty_blocks.append(
                "Unbekannter 'result'-Inhalt:\n\n```json\n" +
                json.dumps(result, ensure_ascii=False, indent=2) +
                "\n```"
            )

    pretty_md = ("\n\n---\n\n").join(pretty_blocks) if pretty_blocks else "_Keine darstellbaren Inhalte_"

    st.markdown("---")
    st.subheader("📘 Aufbereitete Antwort (kopierbar)")
    st.code(pretty_md, language="markdown")
    st.download_button(
        "⬇️ Aufbereitete Antwort als Markdown speichern",
        data=pretty_md.encode("utf-8"),
        file_name="amboss_mcp_pretty.md",
        mime="text/markdown"
    )

    # Ergebnis als Variable verfügbar
    amboss_result = data
    # übrige {Ref...} entfernen
    t = re.sub(r"\{Ref[^\}]+\}", "", t)

    # überflüssige Leerzeichen glätten
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t

def try_parse_embedded_json_text(content_item_text: str):
    """
    Einige Antworten liefern in content[*].text einen JSON-String.
    Diesen versuchen wir zusätzlich zu parsen.
    """
    if not isinstance(content_item_text, str):
        return None
    candidate = fix_mojibake(content_item_text)
    try:
        return json.loads(candidate)
    except Exception:
        return None

def truncate(s: str, n: int = 800) -> str:
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
        arguments["substance_eid"] = query  # benötigt EID (i. d. R. zuvor via search_* ermitteln)
    elif tool_name == "get_guidelines":
        arguments["guideline_ids"] = [query]  # erwartet Liste  ✅ WICHTIG: eckige Klammern geschlossen

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

    # 1) Standardfall: result["results"] (z. B. Suchergebnisse)
    if isinstance(result, dict) and "results" in result:
        st.markdown("### Ergebnisse")
        for item in result["results"]:
            title = item.get("title") or item.get("article_title") or item.get("name") or "–"
            snippet = item.get("snippet") or item.get("chunk") or ""
            url = item.get("url")
            article_id = item.get("article_id") or item.get("eid") or item.get("id")

            pretty = clean_placeholders(snippet, url)

            st.markdown(f"**{fix_mojibake(title)}**")
            if pretty:
                st.markdown(truncate(pretty, 1600), unsafe_allow_html=True)
            if url:
                st.markdown(f"🔗 [Link]({url})")
            if article_id:
                st.caption(f"EID/ID: {article_id}")
            st.markdown("---")

    # 2) Sonderfall: result["content"] ist eine Liste mit Textsegmenten,
    #    das erste Segment enthält oft eingebettetes JSON als String
    elif isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, str):
            st.markdown("### Inhalt (Text)")
            st.markdown(clean_placeholders(content), unsafe_allow_html=True)
        elif isinstance(content, list):
            parsed_any = False
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text" and isinstance(seg.get("text"), str):
                    embedded = try_parse_embedded_json_text(seg["text"])
                    if embedded:
                        parsed_any = True
                        results = embedded.get("results") or embedded.get("data") or []
                        st.markdown("### Extrahierte Ergebnisse (eingebettetes JSON)")
                        if isinstance(results, list) and results:
                            for item in results:
                                title = item.get("title") or item.get("article_title") or "–"
                                snippet = item.get("snippet") or item.get("chunk") or ""
                                url = item.get("url")
                                article_id = item.get("article_id") or item.get("eid") or item.get("id")

                                pretty = clean_placeholders(snippet, url)

                                st.markdown(f"**{fix_mojibake(title)}**")
                                if pretty:
                                    st.markdown(truncate(pretty, 1600), unsafe_allow_html=True)
                                if url:
                                    st.markdown(f"🔗 [Link]({url})")
                                if article_id:
                                    st.caption(f"EID/ID: {article_id}")
                                st.markdown("---")
                        else:
                            st.info("Kein 'results'-Array im eingebetteten JSON – zeige komplettes eingebettetes Objekt:")
                            st.json(embedded)

            if not parsed_any:
                st.markdown("### Inhalt (Segmente)")
                for seg in content:
                    if isinstance(seg, dict) and seg.get("type") == "text":
                        st.markdown(truncate(clean_placeholders(seg.get("text") or ""), 2000),
                                    unsafe_allow_html=True)
                        st.markdown("---")
                    else:
                        st.json(seg)
        else:
            st.info("Unbekanntes 'content'-Format – zeige alles an:")
            st.json(content)

    # 3) Sonst: unbekanntes Schema → komplette Struktur zeigen
    else:
        st.info("Keine standardisierten Felder erkannt – gesamte 'result'-Struktur:")
        st.json(result)

    # 👉 Ergebnis als Variable verfügbar
    amboss_result = data
