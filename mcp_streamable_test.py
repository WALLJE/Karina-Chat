import streamlit as st
import requests
import json
import re

# -----------------------------------------------------------
# 🧩 Grundkonfiguration
# -----------------------------------------------------------
st.set_page_config(page_title="AMBOSS MCP Demo", page_icon="💊")
st.title("💊 AMBOSS MCP – JSON-RPC Beispiel mit Formatierung + Umlaut-Fix")

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

def fix_mojibake(s: str) -> str:
    """
    Repariert typische UTF-8/Latin-1-Mojibake (Ã¼, Ã¤, â€“, Â, …).
    Heuristik: wir interpretieren die bereits dekodierte Zeichenkette
    als Latin-1 Bytes und dekodieren erneut als UTF-8.
    """
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        # Falls das fehlschlägt, ein paar häufige Artefakte ersetzen
        repl = (
            ("â€“", "–"),
            ("â€”", "—"),
            ("â€ž", "„"),
            ("â€œ", "“"),
            ("â€˜", "‚"),
            ("â€™", "’"),
            ("â€¡", "‡"),
            ("â€¢", "•"),
            ("Â", ""),
        )
        for a, b in repl:
            s = s.replace(a, b)
        return s

def clean_placeholders(text: str, url: str | None = None) -> str:
    """
    Wandelt AMBOSS-spezifische Platzhalter in nutzbares Markdown um:
    - {NewLine} -> <br>
    - {Sub}/{/Sub} -> <sub>...</sub>
    - {Sup}/{/Sup} -> <sup>...</sup>
    - {RefNote:ID} -> [†](url)  (ein Symbol)
    - Alle übrigen {Ref...} / {RefXLeft} / {RefYUp} etc. werden entfernt.
    """
    if not isinstance(text, str):
        return text

    t = fix_mojibake(text)

    # Sub/Sup
    t = t.replace("{Sub}", "<sub>").replace("{/Sub}", "</sub>")
    t = t.replace("{Sup}", "<sup>").replace("{/Sup}", "</sup>")

    # NewLine in Tabellen/Zellen
    t = t.replace("{NewLine}", "<br>")

    # RefNote -> †-Link (wenn URL vorhanden), sonst † ohne Link
    if url:
        t = re.sub(r"\{RefNote:[^}]+\}", f"[†]({url})", t)
    else:
        t = re.sub(r"\{RefNote:[^}]+\}", "†", t)

    # Alle übrigen {Ref...}-Platzhalter restlos entfernen (stören Tabelle)
    t = re.sub(r"\{Ref[^\}]+\}", "", t)

    # Einige doppelte Leerzeichen glätten
    t = re.sub(r"[ \t]{2,}", " ", t)

    return t

def try_parse_embedded_json_text(content_item_text: str):
    """
    Einige AMBOSS-Antworten liefern in content[0].text einen JSON-String.
    Den versuchen wir hier zusätzlich zu parsen und zurückzugeben.
    Scheitert das, geben wir None zurück.
    """
    if not isinstance(content_item_text, str):
        return None
    # Vor dem Parsen erst Mojibake fixen, dann versuchen, JSON zu laden
    candidate = fix_mojibake(content_item_text)
    try:
        return json.loads(candidate)
    except Exception:
        # Manchmal ist es tatsächlich reiner Text, kein JSON
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
        arguments["substance_eid"] = query  # benötigt EID (in der Praxis über Suchtool holen)
    elif tool_name == "get_guidelines":
        arguments["guideline_ids"] = [
