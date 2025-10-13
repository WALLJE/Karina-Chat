import streamlit as st
import requests
import json
import re
from typing import Optional, Iterable

# -----------------------------------------------------------
# Grundkonfiguration
# -----------------------------------------------------------
st.set_page_config(page_title="AMBOSS MCP Demo (kompakt)", page_icon="💊")
st.title("💊 AMBOSS MCP – Kompakte Version mit structuredContent & Tabellen-Fix")

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
    """Bereinigt AMBOSS-Platzhalter und setzt †-Links."""
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

# --- Tabellen-Formatierer -----------------------------------------------------
def format_markdown_tables(md: str) -> str:
    """Bereinigt Markdown-Tabellen und verhindert IndexError bei Ein-Zeilen-Tabellen."""

    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    table_pat = re.compile(r"^\s*\|.*\|\s*$")

    def clean_cell(cell: str) -> str:
        cell = cell.strip()
        # führende/abschließende <br> entfernen
        cell = re.sub(r"^(?:<br>\s*)+", "", cell)
        cell = re.sub(r"(?:\s*<br>)+$", "", cell)
        # Platzhalter aufräumen
        cell = cell.replace("{NewLine}", "<br>")
        cell = re.sub(r"\{Ref[^}]*\}", "", cell)
        # Mehrfachspaces normalisieren
        cell = re.sub(r"[ \t]{2,}", " ", cell).strip()
        return cell

    def is_sep_cell(c: str) -> bool:
        cs = c.strip()
        return len(cs) >= 3 and set(cs) <= set("-: ")

    while i < n:
        line = lines[i]
        if table_pat.match(line):
            block: list[str] = []
            while i < n and table_pat.match(lines[i]):
                block.append(lines[i])
                i += 1

            rows: list[list[str]] = []
            max_cols = 0
            for raw_row in block:
                cells = [clean_cell(part) for part in raw_row.strip().strip("|").split("|")]
                if cells:
                    max_cols = max(max_cols, len(cells))
                rows.append(cells)

            if max_cols == 0:
                # Degenerierte Tabellen (z. B. nur "||") bleiben unverändert, damit nichts crasht.
                out.extend(block)
                continue

            if len(rows) == 1:
                # Einzeilige Tabellen bekommen eine künstliche Trennzeile, um Indexfehler zu vermeiden.
                rows.append(["---"] * max_cols)
            elif len(rows) >= 2:
                def is_separator(cell: str) -> bool:
                    cleaned = cell.strip()
                    return len(cleaned) >= 3 and set(cleaned) <= set("-: ")

                if not all(is_separator(cell) for cell in rows[1]):
                    rows.insert(1, ["---"] * max_cols)

            for row in rows:
                if len(row) < max_cols:
                    row.extend([""] * (max_cols - len(row)))

            for row in rows:
                out.append("| " + " | ".join(row) + " |")
            continue

        out.append(line)
        i += 1

    return "\n".join(out)

# --- Ergebnisse extrahieren/rendern ------------------------------------------
def extract_items_from_result(result: dict) -> list[dict]:
    """Gibt Ergebnis-Items zurück, bevorzugt structuredContent.results."""
    if not isinstance(result, dict):
        return []
    sc = result.get("structuredContent")
    if isinstance(sc, dict):
        sc_results = sc.get("results")
        if isinstance(sc_results, list) and sc_results:
            return sc_results
    res = result.get("results")
    if isinstance(res, list) and res:
        return res
    return []

def render_items(items: Iterable[dict]) -> list[str]:
    """Konvertiert Ergebnis-Items in Markdown-Blöcke inkl. Tabellen-Fix."""
    blocks = []
    for it in items:
        title = it.get("title") or it.get("article_title") or it.get("name") or "–"
        snippet = it.get("snippet") or it.get("chunk") or ""
        url = it.get("url")
        eid = it.get("article_id") or it.get("eid") or it.get("id")
        pretty = clean_placeholders(snippet, url)
        try:
            # Fail-Safe: Tabellenaufbereitung darf das Rendering nicht komplett stoppen.
            pretty = format_markdown_tables(pretty)
        except Exception:
            # Wir behalten den bereinigten Text bei und zeigen keine Fehlermeldung im Nutzerfluss.
            pretty = pretty
        block = f"**{fix_mojibake(title)}**\n\n{pretty}"
        if url:
            block += f"\n\n🔗 {url}"
        if eid:
            block += f"\n\n_EID/ID: {eid}_"
        blocks.append(block)
    return blocks

def build_pretty_markdown(data: dict) -> str:
    """Erzeugt die aufbereitete Markdown-Ausgabe (mit structuredContent & Tabellen-Fix)."""
    if "error" in data:
        err = data["error"]
        msg = err.get("message", "Unbekannter Fehler")
        code = err.get("code")
        return f"**Fehler:** {msg}" + (f" (Code {code})" if code is not None else "")

    result = data.get("result", {})

    # 1) Ergebnisse aus structuredContent.results ODER result.results
    items = extract_items_from_result(result)
    if items:
        md_blocks = ["### Ergebnisse"]
        md_blocks.extend(render_items(items))
        return ("\n\n---\n\n").join(md_blocks)

    # 2) content: Segmente oder eingebettetes JSON
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, str):
            md = "### Inhalt (Text)\n\n" + clean_placeholders(content)
            md = fix_inline_table_breaks(md)
            return format_markdown_tables(md)
        if isinstance(content, list):
            embedded_blocks, parsed_any = [], False
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text" and isinstance(seg.get("text"), str):
                    embedded = try_parse_embedded_json_text(seg["text"])
                    if embedded:
                        parsed_any = True
                        emb_items = embedded.get("results") or embedded.get("data") or []
                        if isinstance(emb_items, list) and emb_items:
                            embedded_blocks.extend(render_items(emb_items))
                        else:
                            embedded_blocks.append("```json\n" + json.dumps(embedded, ensure_ascii=False, indent=2) + "\n```")
            if parsed_any and embedded_blocks:
                return ("\n\n").join(["### Extrahierte Ergebnisse (eingebettetes JSON)"] + embedded_blocks)
            # Fallback: rohe Segmente bereinigt
            segment_blocks = []
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text":
                    p = clean_placeholders(seg.get("text") or "")
                    p = fix_inline_table_breaks(p)
                    p = format_markdown_tables(p)
                    segment_blocks.append(p)
                else:
                    segment_blocks.append("```json\n" + json.dumps(seg, ensure_ascii=False, indent=2) + "\n```")
            return ("\n\n---\n\n").join(["### Inhalt (Segmente)"] + segment_blocks)

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

    # Aufbereitete Darstellung – gerendert + copy-friendly
    pretty_md = build_pretty_markdown(data)
    # finaler Sicherheitsdurchlauf
    pretty_md = fix_inline_table_breaks(pretty_md)
    pretty_md = format_markdown_tables(pretty_md)

    st.markdown("---")
    st.subheader("📘 Aufbereitete Antwort (gerendert)")
    st.markdown(pretty_md, unsafe_allow_html=True)

    st.subheader("📋 Aufbereitete Antwort (zum Kopieren)")
    st.code(pretty_md, language="markdown")
    st.download_button("⬇️ Aufbereitete Antwort als Markdown speichern",
                       data=pretty_md.encode("utf-8"),
                       file_name="amboss_mcp_pretty.md", mime="text/markdown")

    # Ergebnis als Variable verfügbar
    amboss_result = data
