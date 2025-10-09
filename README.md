# Karina-Chat

## LLM-Integration – aktueller Stand

Die Anwendung kann wahlweise einen medizinischen MCP-Server oder den regulären ChatGPT-Client von OpenAI nutzen. Beide Varianten werden über `module/llm_state.py` verwaltet und stehen den Streamlit-Seiten unter `st.session_state["mcp_client"]` zur Verfügung.

* **Zentrale Instanzierung**: Beim Start des Hauptskripts (`Karina_Chat_2.py`) ruft die App `ensure_llm_client()` auf. Der erzeugte Client (MCP oder OpenAI) wird im Session-State abgelegt und von allen Unterseiten wiederverwendet.
* **Fallback für Direktaufrufe**: Öffnet jemand eine Unterseite direkt, sorgt `ensure_llm_client()` für eine nachträgliche Initialisierung auf Basis der aktuellen Provider-Auswahl.
* **Admin-Auswahl**: Im Adminbereich lässt sich der aktive LLM-Provider (MCP oder ChatGPT) umschalten. Die Einstellung gilt global für alle Module; fehlende Zugangsdaten werden unmittelbar gemeldet.
* **Offline-Modus**: Ist der Offline-Modus aktiv (`st.session_state["offline_mode"] = True`), deaktiviert die App sämtliche externen LLM-Anfragen und greift auf Platzhalter-Funktionen aus `module/offline.py` zurück.

## Konfiguration der LLM-Clients

### MCP-Server

Die folgenden Umgebungsvariablen steuern den MCP-Zugriff:

| Variable | Pflicht? | Beschreibung |
| --- | --- | --- |
| `MCP_SERVER_URL` | ✅ | Basis-URL des MCP-Servers (z. B. `https://mcp.example.org`). |
| `MCP_API_KEY` | ⛔ optional | API-Schlüssel für den MCP-Server. Wird als `Authorization`-Header gesendet, falls gesetzt. |
| `MCP_MODEL` | ⛔ optional | Standardmodell für Chat-Completions; kann pro Aufruf überschrieben werden. |
| `MCP_TIMEOUT` | ⛔ optional | Timeout in Sekunden für HTTP-Anfragen (Standard: 60). |
| `MCP_AUTH_HEADER` | ⛔ optional | Alternativer Headername für den Authentifizierungstoken. |
| `MCP_CHAT_COMPLETIONS_PATH` | ⛔ optional | Pfad der Chat-Completion-Route, standardmäßig `/v1/chat/completions`. |
| `MCP_EXTRA_HEADERS` | ⛔ optional | JSON-kodiertes Objekt mit zusätzlichen Headern (z. B. `{ "x-tenant": "medizin" }`). |

Fehlt `MCP_SERVER_URL`, schaltet die Anwendung automatisch in den Offline-Modus und nutzt ausschließlich die statischen Platzhalter aus `module/offline.py`.

#### Streamlit-Secrets hinterlegen

Beim Betrieb über Streamlit (lokal mit `streamlit run` oder in Streamlit Cloud) wird das AMBOSS-Zugangs-Token aus `st.secrets["Amboss_Token"]` gelesen. Hinterlegen Sie den Schlüssel daher in den Streamlit-Secrets, zum Beispiel:

```
Amboss_Token = "YOUR-PARTNER-MCP-KEY"
```

Für lokale Tests kann alternativ eine `.streamlit/secrets.toml` mit demselben Eintrag verwendet oder der Schlüssel per `--token` an `test_mcp_connectivity.py` übergeben werden. Das Skript greift nur auf den benötigten Eintrag zu und lädt keine weiteren Secrets. Mit `--interactive` lässt sich im Terminal eine einfache REPL starten, über die beliebige MCP-Tools samt JSON-Argumenten getestet werden können. Wird das Skript via `streamlit run` gestartet, erscheinen die Ergebnisse direkt in der Weboberfläche – inklusive Auswahlbox und JSON-Feld zum Ausprobieren einzelner Tools.

### OpenAI / ChatGPT

Für den OpenAI-Client kommen folgende Variablen zum Einsatz:

| Variable | Pflicht? | Beschreibung |
| --- | --- | --- |
| `OPENAI_API_KEY` | ✅ | API-Schlüssel für das gewünschte OpenAI-Konto. |
| `OPENAI_MODEL` / `OPENAI_DEFAULT_MODEL` | ⛔ optional | Standardmodell für Chat-Completions (z. B. `gpt-4o`). |
| `OPENAI_BASE_URL` | ⛔ optional | Alternative Basis-URL (z. B. für Azure- oder Proxy-Setups). |
| `OPENAI_ORG` | ⛔ optional | Organisation, falls mehrere Organisationen verwaltet werden. |

Ist keine dieser Variablen gesetzt oder das `openai`-Paket nicht installiert, steht der ChatGPT-Client im Adminbereich nicht zur Verfügung.

Netzwerk- oder Serverfehler werden als `MCPClientError` angezeigt; spezifische 429-Antworten lösen einen `RateLimitError` aus, den die UI als Überlastung des aktuell gewählten LLM-Dienstes meldet.

## Auswirkungen auf die Module

* **Anamnese, Untersuchung, Diagnostik, Diagnose/Therapie, Feedback**: Sämtliche Seiten greifen nun auf `st.session_state["mcp_client"]` zu. Jede Seite prüft selbstständig, ob der Client verfügbar ist, um Direktaufrufe robust zu unterstützen.
* **Tokenzählung**: Das Token-Tracking (`module/token_counter.py`) bleibt bestehen. Der MCP-Client erwartet, dass die Antwort ein optionales `usage`-Objekt liefert; fehlen Tokenwerte, werden automatisch `0` eingetragen.
* **Offline-Unterstützung**: Die Offline-Hinweise betonen, dass keine externen LLM-Anfragen gesendet werden.

## Betrieb & Tests

1. Abhängigkeiten installieren: `pip install -r requirements.txt`
2. Benötigte Umgebungsvariablen setzen (je nach Provider `MCP_*` oder `OPENAI_*`).
3. Streamlit-App starten: `streamlit run Karina_Chat_2.py`

Ohne valide Konfiguration eines LLM-Providers empfiehlt sich der Offline-Modus (z. B. im Adminbereich aktivierbar), um das Frontend ohne Serverzugriff zu demonstrieren.
