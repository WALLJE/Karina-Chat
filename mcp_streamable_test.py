"""Streamlit helper to exercise the AMBOSS MCP streamable HTTP endpoint.

The app mirrors the manual ``--streamableHttp`` setup from the Claude example
and provides a lightweight UI to issue JSON-RPC calls against the AMBOSS MCP
server. A free-text field is available for quickly crafting requests that match
the expected arguments of the selected tool.

Usage::

    streamlit run mcp_streamable_test.py

Provide your partner MCP token either via ``st.secrets["Amboss_Token"]`` or a
local ``.streamlit/secrets.toml`` file with the same key. The token field in the
UI can override both sources when needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import requests
import streamlit as st

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_HTTP_URL = "https://content-mcp.de.production.amboss.com/mcp"
DEFAULT_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
DEFAULT_TIMEOUT = 30.0
DEFAULT_LANGUAGE = "de"


class MCPConnectionError(RuntimeError):
    """Raised when the MCP streamable HTTP request fails."""


@dataclass
class SSEEvent:
    """Representation of a single SSE event emitted by the MCP endpoint."""

    event: Optional[str]
    event_id: Optional[str]
    data: str
    json_payload: Optional[object]


def _load_token_from_streamlit() -> Optional[str]:
    """Return the token from ``st.secrets`` if available."""

    try:
        token = st.secrets["Amboss_Token"]  # type: ignore[index]
    except Exception:
        return None

    return str(token) if token else None


def _load_token_from_file(path: Path) -> Optional[str]:
    """Return the AMBOSS MCP token stored in a secrets TOML file."""

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, tomllib.TOMLDecodeError) as exc:  # pragma: no cover - I/O failure
        raise MCPConnectionError(
            f"Secrets-Datei '{path}' konnte nicht gelesen werden: {exc}"
        ) from exc

    token = data.get("Amboss_Token")
    if isinstance(token, str) and token.strip():
        return token.strip()

    amboss_section = data.get("amboss_mcp")
    if isinstance(amboss_section, dict):
        legacy = amboss_section.get("api_key")
        if isinstance(legacy, str) and legacy.strip():
            return legacy.strip()

    return None


def _load_default_token() -> Optional[str]:
    """Try to load the MCP token from Streamlit secrets or the local TOML file."""

    token = _load_token_from_streamlit()
    if token:
        return token
    return _load_token_from_file(DEFAULT_SECRETS_PATH)


def _build_headers(api_key: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Create the HTTP headers required for MCP requests."""

    headers = {"Authorization": f"Bearer {api_key}"}
    if extra:
        headers.update(extra)
    return headers


_KNOWN_PRIMARY_ARGUMENTS = {
    "search_article_sections": "query",
    "search_questions": "query",
    "search_pharma_substances": "query",
    "search_media": "query",
    "get_guidelines": "query",
    "get_definition": "term",
}


def _extract_primary_argument(tool: Dict[str, object]) -> Optional[str]:
    """Return the most relevant argument key for free-text inputs."""

    schema = tool.get("input_schema") if isinstance(tool, dict) else None
    if not isinstance(schema, dict):
        name = tool.get("name") if isinstance(tool, dict) else None
        if isinstance(name, str):
            mapped = _KNOWN_PRIMARY_ARGUMENTS.get(name)
            if mapped:
                return mapped
            if name.startswith("search_"):
                return "query"
        return None

    required = schema.get("required")
    if isinstance(required, list):
        for entry in required:
            if isinstance(entry, str) and entry != "language":
                return entry

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key in properties:
            if isinstance(key, str) and key != "language":
                return key

    name = tool.get("name") if isinstance(tool, dict) else None
    if isinstance(name, str):
        mapped = _KNOWN_PRIMARY_ARGUMENTS.get(name)
        if mapped:
            return mapped
        if name.startswith("search_"):
            return "query"

    return None


def _parse_arguments_input(
    raw_text: str, *, fallback_key: Optional[str] = None
) -> Dict[str, object]:
    """Parse user-supplied arguments entered as JSON or key/value text."""

    text = raw_text.strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {fallback_key or "items": parsed}

    if fallback_key:
        return {fallback_key: text}

    # Support simple ``key=value`` pairs separated by commas or newlines.
    arguments: Dict[str, object] = {}
    separator = "," if "," in text and "\n" not in text else "\n"
    for chunk in [part.strip() for part in text.split(separator) if part.strip()]:
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            arguments[key.strip()] = value.strip()
        else:
            arguments[chunk] = True
    if arguments:
        return arguments

    raise ValueError(
        "Eingabe konnte nicht verarbeitet werden. Bitte JSON oder key=value verwenden."
    )


def _safe_json_loads(text: str) -> Optional[object]:
    """Best-effort JSON decoder used for SSE payloads."""

    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _iter_sse_events(lines: Iterable[str]) -> Iterator[SSEEvent]:
    """Yield :class:`SSEEvent` objects from an SSE response."""

    current_data: List[str] = []
    event_type: Optional[str] = None
    event_id: Optional[str] = None

    for raw_line in lines:
        if raw_line is None:
            continue
        line = raw_line.rstrip("\r")
        if not line:
            if current_data or event_type or event_id:
                data_text = "\n".join(current_data)
                yield SSEEvent(
                    event=event_type,
                    event_id=event_id,
                    data=data_text,
                    json_payload=_safe_json_loads(data_text),
                )
            current_data = []
            event_type = None
            event_id = None
            continue

        if line.startswith(":"):
            continue  # comment line

        if ":" in line:
            field, value = line.split(":", 1)
            value = value.lstrip()
        else:
            field, value = line, ""

        if field == "data":
            current_data.append(value)
        elif field == "event":
            event_type = value or None
        elif field == "id":
            event_id = value or None
        # ``retry`` is ignored here as it is not relevant for immediate processing.

    if current_data or event_type or event_id:
        data_text = "\n".join(current_data)
        yield SSEEvent(
            event=event_type,
            event_id=event_id,
            data=data_text,
            json_payload=_safe_json_loads(data_text),
        )


def _fetch_tools(url: str, api_key: str, timeout: float) -> List[Dict[str, object]]:
    """Fetch the catalogue of MCP tools using a classic JSON request."""

    payload = {
        "jsonrpc": "2.0",
        "id": "tools/list",
        "method": "tools/list",
        "params": {},
    }
    headers = _build_headers(
        api_key,
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise MCPConnectionError(f"HTTP-Anfrage an das MCP-Endpoint ist fehlgeschlagen: {exc}") from exc

    if response.status_code == 401:
        raise MCPConnectionError("Authentifizierung fehlgeschlagen – bitte MCP-Token prüfen.")
    if response.status_code == 403:
        raise MCPConnectionError("Zugriff verweigert – fehlen eventuell Berechtigungen?")
    if response.status_code >= 400:
        raise MCPConnectionError(
            f"Fehlerhafte Antwort vom MCP-Endpoint ({response.status_code}): {response.text.strip()}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise MCPConnectionError(f"Antwort konnte nicht als JSON interpretiert werden: {exc}") from exc

    tools = data.get("result", {}).get("tools")
    if not isinstance(tools, list):
        raise MCPConnectionError(
            "Die Antwort enthielt keine gültige Tool-Liste (result.tools)."
        )
    return tools  # type: ignore[return-value]


def _stream_tool_call(
    url: str,
    api_key: str,
    *,
    name: str,
    arguments: Dict[str, object],
    timeout: float,
) -> Iterator[Dict[str, object]]:
    """Stream a tool invocation via the MCP HTTP endpoint."""

    payload = {
        "jsonrpc": "2.0",
        "id": f"tools/call:{name}",
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments,
        },
    }
    headers = _build_headers(
        api_key,
        {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
            stream=True,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise MCPConnectionError(f"HTTP-Anfrage an das MCP-Endpoint ist fehlgeschlagen: {exc}") from exc

    if response.status_code == 401:
        raise MCPConnectionError("Authentifizierung fehlgeschlagen – bitte MCP-Token prüfen.")
    if response.status_code == 403:
        raise MCPConnectionError("Zugriff verweigert – fehlen eventuell Berechtigungen?")
    if response.status_code >= 400:
        body = response.text
        raise MCPConnectionError(
            f"Fehlerhafte Antwort vom MCP-Endpoint ({response.status_code}): {body.strip()}"
        )

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/event-stream" in content_type:
        last_json: Optional[object] = None
        last_data: str = ""
        for event in _iter_sse_events(response.iter_lines(decode_unicode=True)):
            if event.json_payload is not None:
                last_json = event.json_payload
            if event.data:
                last_data = event.data
            yield {
                "kind": "event",
                "event": event.event,
                "id": event.event_id,
                "data": event.data,
                "json": event.json_payload,
            }
        yield {
            "kind": "final",
            "json": last_json,
            "raw": json.dumps(last_json, ensure_ascii=False) if last_json is not None else last_data,
        }
        return

    # Fallback: standard JSON response without SSE framing.
    body_text = response.text
    json_payload = _safe_json_loads(body_text)
    yield {
        "kind": "final",
        "json": json_payload,
        "raw": body_text,
    }


@st.cache_data(show_spinner=False)
def _cached_tools(url: str, token: str, timeout: float) -> List[Dict[str, object]]:
    """Cached wrapper around :func:`_fetch_tools` for Streamlit reruns."""

    return _fetch_tools(url, token, timeout)


def _render_tool_description(tool: Dict[str, object]) -> None:
    """Render the tool description with Markdown paragraphs."""

    description = tool.get("description")
    if isinstance(description, str) and description.strip():
        for block in description.strip().split("\n\n"):
            st.markdown(block.strip())


def _ensure_token(token: str) -> str:
    """Validate that a token is available before performing requests."""

    if not token.strip():
        raise MCPConnectionError(
            "Es wurde kein MCP-Token bereitgestellt. Bitte im Formular eintragen."
        )
    return token.strip()


def main() -> None:
    st.set_page_config(page_title="AMBOSS MCP Streamable HTTP Test", page_icon="🩺")
    st.title("AMBOSS MCP Streamable HTTP Test")
    st.write(
        "Dieses Hilfswerkzeug stellt eine Verbindung zum streambaren HTTP-Endpunkt "
        "des AMBOSS MCP her. Wählen Sie ein Tool aus, geben Sie Ihre Anfrage in das "
        "Textfeld ein und verfolgen Sie die einzelnen SSE-Ereignisse direkt im Browser."
    )

    stored_token = _load_default_token()
    token_input = st.text_input(
        "AMBOSS MCP Token",
        type="password",
        help=(
            "Token hier eingeben, um lokale Secrets zu überschreiben. Wenn leer, werden "
            "st.secrets bzw. .streamlit/secrets.toml verwendet."
        ),
    ).strip()
    api_key = token_input or (stored_token or "")

    if stored_token and not token_input:
        st.caption("Token wurde automatisch aus Secrets geladen. Eingabe überschreibt den Wert.")

    http_url = st.text_input("MCP HTTP Endpoint", value=DEFAULT_HTTP_URL)
    timeout = st.slider(
        "Timeout (Sekunden)",
        min_value=5.0,
        max_value=120.0,
        value=DEFAULT_TIMEOUT,
        step=5.0,
    )
    language = st.selectbox(
        "Sprache", options=["de", "en"], index=0 if DEFAULT_LANGUAGE == "de" else 1
    )

    tools: List[Dict[str, object]] = []
    if api_key:
        try:
            tools = _cached_tools(http_url, api_key, timeout)
        except MCPConnectionError as exc:
            st.error(str(exc))
    else:
        st.info("Bitte MCP-Token angeben, um die Tool-Liste laden zu können.")

    tool_names = [tool.get("name", "") for tool in tools if tool.get("name")]
    selected_tool_name = st.selectbox(
        "Tool auswählen",
        options=tool_names if tool_names else [""],
        index=0,
        disabled=not tool_names,
    )

    selected_tool = next(
        (tool for tool in tools if tool.get("name") == selected_tool_name),
        {},
    ) if selected_tool_name else {}

    if selected_tool:
        _render_tool_description(selected_tool)

    primary_argument = _extract_primary_argument(selected_tool)
    if primary_argument:
        st.caption(
            f"Freitext wird automatisch als Argument '{primary_argument}' interpretiert."
        )
    else:
        st.caption(
            "Eingabe kann als JSON oder als Liste von key=value Paaren erfolgen."
        )

    user_input = st.text_area(
        "Eingabefeld",
        value="",
        placeholder="Suchbegriff oder JSON-Argumente",
    )

    if st.button("Anfrage senden", type="primary"):
        try:
            api_key = _ensure_token(api_key)
        except MCPConnectionError as exc:
            st.error(str(exc))
            return

        if not selected_tool_name:
            st.error("Bitte zuerst ein Tool auswählen.")
            return

        try:
            parsed_arguments = _parse_arguments_input(
                user_input,
                fallback_key=primary_argument,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        arguments: Dict[str, object] = {}
        if language:
            arguments["language"] = language
        arguments.update(parsed_arguments)

        placeholder = st.empty()
        events_log: List[str] = []
        final_json: Optional[object] = None
        final_raw: str = ""

        try:
            with st.spinner("Anfrage wird ausgeführt…"):
                for update in _stream_tool_call(
                    http_url,
                    api_key,
                    name=selected_tool_name,
                    arguments=arguments,
                    timeout=timeout,
                ):
                    if update["kind"] == "event":
                        event_name = update.get("event") or "message"
                        data = update.get("data") or "(kein Datenfeld)"
                        snippet = data if len(data) < 500 else data[:500] + "…"
                        events_log.append(
                            f"**Event:** `{event_name}`\n\n```text\n{snippet}\n```"
                        )
                        placeholder.markdown("\n\n".join(events_log))
                    elif update["kind"] == "final":
                        final_json = update.get("json")
                        final_raw = update.get("raw", "")
        except MCPConnectionError as exc:
            st.error(str(exc))
            return

        if final_json is not None:
            st.success("Antwort erfolgreich erhalten.")
            st.json(final_json)
        elif final_raw.strip():
            st.warning("Antwort konnte nicht als JSON interpretiert werden. Rohdaten:")
            st.code(final_raw)
        else:
            st.info("Es wurden keine Daten vom MCP-Server zurückgeliefert.")


if __name__ == "__main__":  # pragma: no cover - Streamlit entry point
    main()
