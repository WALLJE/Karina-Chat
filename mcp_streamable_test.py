import streamlit as st
import requests
import json
import re
from typing import Optional, Iterable

# -----------------------------------------------------------
# Grundkonfiguration
# -----------------------------------------------------------
st.set_page_config(page_title="AMBOSS MCP Demo (kompakt)", page_icon="💊")
st.title("💊 AMBOSS MCP – Kompakte Version")

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

# -----------------------------------------------------------
# Hilfsfunktionen
# -----------------------------------------------------------
def fix_mojibake(s: str) -> str:
    """Repariert typische UTF-8/Latin-1-Mojibake."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        for a, b in (
            ("â€“", "–"), ("â€”", "—"), ("â€ž", "„"), ("â€œ", "“"),
            ("â€˜", "‚"), ("â€™", "’"), ("â€¡", "‡"), ("â€¢", "•"), ("Â", "")
        ):
            s = s.replace(a, b)
        return s

def clean_placeholders(text: str, url: Optional[str] = None) -> str:
    """Bereinigt AMBOSS-spezifische Platzhalter und setzt †-Links."""
    if not isinstance(text, str):
        return text
    t = fix_mojibake(text)
    t = t.replace("{Sub}", "<sub>").replace("{/Sub}", "</sub>")
    t = t.replace("{Sup}", "<sup>").replace("{/Sup}", "</sup>")
    t = t.replace("{NewLine}", "<br>")
    t = re.sub(r"\{RefNote:[^}]+\}", f"[†]({url})" if url else "†", t)
    t = re.sub(r"\{Ref[^\}]+\}", "", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t

def try_parse_json(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        return None

def try_parse_embedded_json_text(content_item_text: str) -> Optional[dict]:
    """Parst eingebetteten JSON-String in content[*].text (falls vorhanden)."""
    if not isinstance(content_item_text, str):
        return None
    return try_parse_json(fix_mojibake(content_item_text))

def parse_mcp_response(resp: requests.Response) -> dict:
    """Liest JSON direkt oder extrahiert es aus SSE-Frames."""
    ctype = resp.headers.get("Content-Type", "")
    if "application/json" in ctype:
        return resp.json()
    # SSE: sammle data:-Zeilen
    payload = "".join(
        line.strip()[len("data:"):].strip()
        for line in resp.text.splitlines()
        if line.strip().startswith("data:")
    )
    parsed = try_parse_json(payload)
    if parsed is None:
        raise ValueError("Konnte SSE-JSON nicht extrahieren.")
    return parsed

def build_payload(tool_name: str, query: str) -> dict:
    """Baut JSON-RPC Payload; mappt Freitext auf passende Argumente je Tool."""
    args = {"language": "de"}
    if tool_name in ("search_article_sections", "search_pharma_substances", "search_media"):
        args["query"] = query
    elif tool_name == "get_definition":
        args["term"] = query
    elif tool_name == "get_drug_monograph":
        args["substance_eid"] = query          # in Praxis via search_* ermitteln
    elif tool_name == "get_guidelines":
        args["guideline_ids"] = [query]        # erwartet Liste
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args},
    }

def render_items(items: Iterable[dict]) -> list[str]:
    """Konvertiert Ergebnis-Items (egal ob aus results oder embedded) in Markdown-Blöcke."""
    blocks = []
    for it in items:
        title = it.get("title") or it.get("article_title") or it.get("name") or "–"
        snippet = it.get("snippet") or it.get("chunk") or ""
        url = it.get("url")
        eid = it.get("article_id") or it.get("eid") or it.get("id")
        pretty = clean_placeholders(snippet, url)
        block = f"**{fix_mojibake(title)}**\n\n{pretty}"
        if url:
            block += f"\n\n🔗 {url}"
        if eid:
            block += f"\n\n_EID/ID: {eid}_"
        blocks.append(block)
    return blocks

def build_pretty_markdown(data: dict) -> str:
    """Erzeugt die aufbereitete Markdown-Ausgabe (kompakt, ohne Dopplungen)."""
    if "error" in data:
        err = data["error"]
        msg = err.get("message", "Unbekannter Fehler")
        code = err.get("code")
        return f"**Fehler:** {msg}" + (f" (Code {code})" if code is not None else "")

    result = data.get("result", {})
    md_blocks: list[str] = []

    # 1) Direkte results-Liste
    if isinstance(result, dict) and "results" in result:
        items = result.get("results") or []
        if items:
            md_blocks.append("### Ergebnisse")
            md_blocks.extend(render_items(items))
        return ("\n\n---\n\n").join(md_blocks) if md_blocks else "_Keine Ergebnisse_"

    # 2) content: Segmente oder eingebettetes JSON
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        # a) Einfacher Text
        if isinstance(content, str):
            return "### Inhalt (Text)\n\n" + clean_placeholders(content)
        # b) Liste mit Textsegmenten / eingebettetem JSON
        if isinstance(content, list):
            embedded_blocks, parsed_any = [], False
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text" and isinstance(seg.get("text"), str):
                    embedded = try_parse_embedded_json_text(seg["text"])
                    if embedded:
                        parsed_any = True
                        items = embedded.get("results") or embedded.get("data") or []
                        if isinstance(items, list) and items:
                            embedded_blocks.extend(render_items(items))
                        else:
                            embedded_blocks.append("```json\n" + json.dumps(embedded, ensure_ascii=False, indent=2) + "\n```")
            if parsed_any and embedded_blocks:
                return "### Extrahierte Ergebnisse (eingebettetes JSON)\n\n" + ("\n\n---\n\n").join(embedded_blocks)
            # Fallback: rohe Segmente bereinigt
            segment_blocks = []
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text":
                    segment_blocks.append(clean_placeholders(seg.get("text") or ""))
                else:
                    segment_blocks.append("```json\n" + json.dumps(seg, ensure_ascii=False, indent=2) + "\n```")
            return "### Inhalt (Segmente)\n\n" + ("\n\n---\n\n").join(segment_blocks)

        # Unbekanntes content-Format
        return "Unbekanntes 'content'-Format:\n\n```json\n" + json.dumps(content, ensure_ascii=False, indent=2) + "\n```"

    # 3) Sonst – komplettes result zeigen
    return "Unbekannter 'result'-Inhalt:\n\n```json\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n```"

# -----------------------------------------------------------
# UI
# -----------------------------------------------------------
tool_label = st.selectbox("Welches AMBOSS-Tool möchtest du verwenden?", list(TOOLS.keys()))
tool_name = TOOLS[tool_label]
query = st.text_input("🔍 Freitext (z. B. 'Mesalazin', 'Ileitis terminalis' oder eine EID/ID)")

if st.button("📤 Anfrage an AMBOSS senden"):
    payload = build_payload(tool_name, query)
    headers = {
        "Authorization": f"Bearer {AMBOSS_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    st.write("⏳ Anfrage wird gesendet …")
    resp = requests.post(AMBOSS_URL, headers=headers, data=json.dumps(payload), timeout=30)

    # Rohparsing (JSON oder SSE)
    try:
        data = parse_mcp_response(resp)
    except Exception as e:
        st.error(f"Fehler beim Parsen der Antwort: {e}")
        st.text(resp.text)
        st.stop()

    # Rohdaten – copy-friendly + Download
    st.success("✅ Antwort von AMBOSS erhalten (Rohdaten):")
    raw_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.code(raw_str, language="json")
    st.download_button("⬇️ Rohantwort als JSON speichern", data=raw_str.encode("utf-8"),
                       file_name="amboss_mcp_raw.json", mime="application/json")

    # Aufbereitete Darstellung – copy-friendly + Download
    pretty_md = build_pretty_markdown(data)
    st.markdown("---")
    st.subheader("📘 Aufbereitete Antwort (kopierbar)")
    st.code(pretty_md, language="markdown")
    st.download_button("⬇️ Aufbereitete Antwort als Markdown speichern",
                       data=pretty_md.encode("utf-8"),
                       file_name="amboss_mcp_pretty.md", mime="text/markdown")

    # Ergebnis als Variable verfügbar
    amboss_result = data
