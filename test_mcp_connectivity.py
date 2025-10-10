"""Utility script to validate access to the AMBOSS MCP endpoints.

The script expects the AMBOSS partner token to be available via
``st.secrets["Amboss_Token"]`` (when executed with ``streamlit run``) or, as a
fallback, in a dedicated TOML file.  It performs two optional checks:

1. Establishing an authenticated SSE connection to verify that the streaming
   endpoint accepts the provided API key.
2. Listing the available tools and, optionally, calling a specific MCP tool via
   the streamable HTTP endpoint.

Both checks are useful to confirm that networking, authentication and the MCP
server itself are working before wiring the credentials into the main
application.  When run in a terminal the script can start an interactive
REPL (``--interactive``) to call arbitrary tools.  Executed via Streamlit, the
results are rendered in the browser together with simple controls for invoking
tools.

Usage examples::

    python test_mcp_connectivity.py                 # run HTTP and SSE checks
    python test_mcp_connectivity.py --no-sse        # skip the SSE check
    python test_mcp_connectivity.py --tool list_all_articles --language de

When using Streamlit Cloud or ``streamlit run``, add the token to the secrets
configuration (e.g. via the "Secrets" editor)::

    Amboss_Token = "YOUR-PARTNER-MCP-KEY"

If a TOML file is preferred locally, pass ``--secrets-path`` and ensure the
file contains the same key/value pair.

Optional command line flags can override the HTTP/SSE endpoints, language and
timeout. If no SSE URL is provided the SSE check is skipped automatically.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

import requests

try:  # pragma: no cover - optional dependency
    import streamlit as st
except Exception:  # pragma: no cover - streamlit unavailable
    st = None  # type: ignore[assignment]

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
DEFAULT_HTTP_URL = "https://content-mcp.de.production.amboss.com/mcp"
DEFAULT_SSE_URL = "https://content-mcp.de.production.amboss.com/sse"


class MCPConnectionError(RuntimeError):
    """Raised when the MCP connectivity test fails."""


def _load_token_from_streamlit() -> Optional[str]:
    """Return the token from ``st.secrets`` if available."""

    if st is None:  # Streamlit not installed
        return None

    try:
        secrets = st.secrets  # type: ignore[attr-defined]
    except Exception:
        return None

    try:
        token = secrets["Amboss_Token"]
    except KeyError:
        return None

    return str(token) if token else None


def _load_token_from_file(path: Path) -> str:
    """Return the AMBOSS MCP token stored in a secrets TOML file."""

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise MCPConnectionError(
            f"Secrets file '{path}' not found. Pass --secrets-path if it lives elsewhere."
        ) from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:  # pragma: no cover - I/O failure
        raise MCPConnectionError(f"Failed to read secrets file '{path}': {exc}") from exc

    token: Optional[Any] = data.get("Amboss_Token")

    # Backwards compatibility with the previous [amboss_mcp] format.
    if token is None and isinstance(data.get("amboss_mcp"), dict):
        token = data["amboss_mcp"].get("api_key")

    if not token or not isinstance(token, str):
        raise MCPConnectionError(
            "The secrets file must contain an 'Amboss_Token' entry with your MCP key."
        )

    return token


def load_amboss_token(path: Optional[Path]) -> str:
    """Return the AMBOSS MCP token from Streamlit secrets or a TOML file."""

    token = _load_token_from_streamlit()
    if token:
        return token

    if path is None:
        raise MCPConnectionError(
            "No MCP token found in st.secrets and no secrets file path provided. "
            "Add 'Amboss_Token' to your Streamlit secrets or pass --secrets-path."
        )

    return _load_token_from_file(path)


def _is_running_with_streamlit() -> bool:
    """Return ``True`` when the script runs inside a Streamlit app."""

    if st is None:
        return False

    # ``st._is_running_with_streamlit`` existed in older releases. Some hosted
    # environments no longer set it, therefore we fall back to the official
    # runtime helper if available.
    if getattr(st, "_is_running_with_streamlit", False):
        return True

    try:  # pragma: no cover - depends on Streamlit internals
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:  # pragma: no cover - runtime helper unavailable
        return False

    return get_script_run_ctx() is not None


def _coerce_scalar(value: str) -> Any:
    """Convert a simple textual value to a JSON-compatible scalar."""

    text = value.strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None

    # Try numeric conversion before falling back to JSON parsing.
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        pass

    if (text.startswith("[") and text.endswith("]")) or (
        text.startswith("{") and text.endswith("}")
    ):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]

    return text


def _parse_arguments_input(
    raw_text: str, *, fallback_key: Optional[str] = None
) -> Dict[str, Any]:
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
    if isinstance(parsed, str) and fallback_key:
        return {fallback_key: parsed}

    if fallback_key and not any(sep in text for sep in ("=", ":")):
        return {fallback_key: text}

    # Fallback: allow users to enter simple key=value pairs per line or comma separated.
    entries: Dict[str, Any] = {}
    candidate_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        candidate_lines.extend(part for part in stripped.split(",") if part.strip())

    for item in candidate_lines:
        entry = item.strip().rstrip(",")
        if "=" in entry:
            key, value = entry.split("=", 1)
        elif ":" in entry and (": " in entry or " :" in entry):
            key, value = entry.split(":", 1)
        else:
            if fallback_key and not entries:
                return {fallback_key: text}
            raise ValueError(
                "Argumentzeilen müssen entweder 'schlüssel=wert' oder 'schlüssel: wert' enthalten."
            )

        key = key.strip()
        if not key:
            raise ValueError("Argumentschlüssel dürfen nicht leer sein.")

        entries[key] = _coerce_scalar(value)

    return entries


def _render_tool_description(tool: Dict[str, Any]) -> None:
    """Render the tool description with expandable details in Streamlit."""

    if st is None:
        return

    description = tool.get("description")
    if not isinstance(description, str):
        return

    paragraphs = [part.strip() for part in description.split("\n\n") if part.strip()]
    if not paragraphs:
        return

    st.markdown(paragraphs[0])
    if len(paragraphs) > 1:
        with st.expander("Weitere Hinweise", expanded=False):
            for paragraph in paragraphs[1:]:
                st.markdown(paragraph)


def build_headers(api_key: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
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


def _extract_primary_argument_name(tool: Dict[str, Any]) -> Optional[str]:
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
        for name in required:
            if isinstance(name, str) and name != "language":
                return name

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name in properties:
            if isinstance(name, str) and name != "language":
                return name

    tool_name = tool.get("name") if isinstance(tool, dict) else None
    if isinstance(tool_name, str):
        mapped = _KNOWN_PRIMARY_ARGUMENTS.get(tool_name)
        if mapped:
            return mapped
        if tool_name.startswith("search_"):
            return "query"

    return None


PLACEHOLDER_REPLACEMENTS = {
    "{Sub}": "<sub>",
    "{/Sub}": "</sub>",
    "{Sup}": "<sup>",
    "{/Sup}": "</sup>",
    "{NewLine}": "<br />",
}

_FOOTNOTE_REF_PATTERN = re.compile(r"\{RefNote:([^}]+)\}")
_FOOTNOTE_PATTERN = re.compile(r"\{Note:([^}]+)\}")


def _normalise_placeholders(text: str) -> str:
    """Replace custom MCP placeholders with HTML/Markdown equivalents."""

    normalised = text
    for needle, replacement in PLACEHOLDER_REPLACEMENTS.items():
        normalised = normalised.replace(needle, replacement)

    normalised = normalised.replace("{RefYUp}", "").replace("{RefXLeft}", "").replace(
        "{RefYUpXLeft}", ""
    ).replace("{/Note}", "")
    normalised = _FOOTNOTE_REF_PATTERN.sub(r"[Fußnote \1]", normalised)
    normalised = _FOOTNOTE_PATTERN.sub(r"**Fußnote \1:**", normalised)
    return normalised


def _extract_textual_payload(data: Any) -> Optional[str]:
    """Try to extract a human-readable text payload from tool results."""

    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        for key in ("text", "content", "markdown", "response", "result"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                joined = _extract_textual_payload(value)
                if joined:
                    return joined
            if isinstance(value, dict):
                nested = _extract_textual_payload(value)
                if nested:
                    return nested

    if isinstance(data, list):
        parts = [part for part in (_extract_textual_payload(item) for item in data) if part]
        if parts:
            return "\n\n".join(parts)

    return None


def _render_streamlit_result(result: Any) -> None:
    """Display tool results in Streamlit using readable Markdown."""

    if st is None:
        return

    text_payload = _extract_textual_payload(result)
    if text_payload:
        st.markdown(_normalise_placeholders(text_payload), unsafe_allow_html=True)
        with st.expander("Rohdaten anzeigen"):
            st.json(result)
    else:
        st.json(result)


class Reporter:
    """Utility class that abstracts printing vs. Streamlit rendering."""

    def section(self, title: str) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def info(self, message: str) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def bullet(self, title: str, body: str) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def json(self, data: Any) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class ConsoleReporter(Reporter):
    """Reporter that writes results to stdout."""

    def section(self, title: str) -> None:
        print(f"=== {title} ===")

    def info(self, message: str) -> None:
        print(message)

    def bullet(self, title: str, body: str) -> None:
        print(f"- {title}: {body}")

    def json(self, data: Any) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=False))


class StreamlitReporter(Reporter):
    """Reporter that renders output via Streamlit widgets."""

    def __init__(self) -> None:
        if st is None:
            raise RuntimeError("Streamlit is not available")
        self._container = st.container()

    def section(self, title: str) -> None:
        self._container.subheader(title)

    def info(self, message: str) -> None:
        self._container.write(message)

    def bullet(self, title: str, body: str) -> None:
        self._container.markdown(f"- **{title}**: {body}")

    def json(self, data: Any) -> None:
        self._container.json(data)


def check_sse_endpoint(url: str, api_key: str, timeout: float, reporter: Reporter) -> None:
    """Attempt to open the SSE stream and print the first line if available."""

    reporter.info(f"Connecting to SSE endpoint: {url}")
    headers = build_headers(api_key, {"Accept": "text/event-stream"})

    try:
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                raise MCPConnectionError(
                    f"SSE endpoint returned status {resp.status_code}: {resp.text.strip()}"
                )

            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    reporter.info(f"First SSE event line: {line}")
                    break
            else:
                reporter.info("SSE connection established but no events were received (yet).")
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise MCPConnectionError(f"Failed to connect to SSE endpoint: {exc}") from exc


def send_mcp_request(url: str, api_key: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """Send a JSON request to the MCP HTTP endpoint and return the decoded response."""

    headers = build_headers(
        api_key,
        {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise MCPConnectionError(f"HTTP request to MCP endpoint failed: {exc}") from exc

    if response.status_code == 401:
        raise MCPConnectionError("Authentication failed – check your MCP API key.")
    if response.status_code == 403:
        raise MCPConnectionError("Access forbidden – the MCP key may lack the required permissions.")
    if response.status_code >= 400:
        raise MCPConnectionError(
            f"MCP endpoint returned status {response.status_code}: {response.text.strip()}"
        )

    if not response.content:
        raise MCPConnectionError("MCP endpoint returned an empty response.")

    content_type = response.headers.get("Content-Type", "")
    body_text = response.text

    # Some MCP servers reply to tool invocations using server-sent events even on
    # the HTTP endpoint when the ``Accept`` header includes ``text/event-stream``.
    # In that case we need to extract the JSON payload from the SSE ``data:``
    # lines before attempting to decode the response.
    if "text/event-stream" in content_type or body_text.lstrip().startswith("event:"):
        data_lines: list[str] = []
        for line in body_text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line.strip() and data_lines:
                # Blank line signals the end of the first SSE event.
                break

        if not data_lines:
            raise MCPConnectionError(
                "Received an SSE response without any data payload to decode."
            )

        body_text = "\n".join(data_lines)

    try:
        data = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise MCPConnectionError(
            f"Response was not valid JSON: {exc}. Raw payload: {body_text[:200]}"
        ) from exc

    if isinstance(data, dict) and data.get("error"):
        raise MCPConnectionError(
            "MCP server returned an error: " + json.dumps(data.get("error"), ensure_ascii=False)
        )

    return data


def list_tools(url: str, api_key: str, timeout: float) -> Iterable[Dict[str, Any]]:
    """Request the catalogue of MCP tools."""

    payload = {
        "jsonrpc": "2.0",
        "id": "tools/list",
        "method": "tools/list",
        "params": {},
    }

    data = send_mcp_request(url, api_key, payload, timeout)
    tools = data.get("result", {}).get("tools")
    if not isinstance(tools, list):
        raise MCPConnectionError(
            "The MCP response did not contain a 'result.tools' list. "
            "Raw response: " + json.dumps(data, ensure_ascii=False)
        )
    return tools


def call_tool(
    url: str,
    api_key: str,
    *,
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
    timeout: float,
) -> Dict[str, Any]:
    """Invoke a specific MCP tool and return the decoded result."""

    payload = {
        "jsonrpc": "2.0",
        "id": f"tools/call:{name}",
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments or {},
        },
    }
    data = send_mcp_request(url, api_key, payload, timeout)
    result = data.get("result")
    if result is None:
        raise MCPConnectionError(
            "The MCP response did not contain a 'result' field. "
            "Raw response: " + json.dumps(data, ensure_ascii=False)
        )
    return result


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--secrets-path",
        type=Path,
        default=DEFAULT_SECRETS_PATH,
        help=(
            "Path to a local Streamlit secrets TOML file. If omitted the script tries "
            "st.secrets['Amboss_Token'] first and only reads this file when necessary."
        ),
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="AMBOSS MCP token. Overrides the value loaded from the secrets file.",
    )
    parser.add_argument(
        "--http-url",
        type=str,
        default=DEFAULT_HTTP_URL,
        help="AMBOSS MCP HTTP endpoint (default: %(default)s).",
    )
    parser.add_argument(
        "--sse-url",
        type=str,
        default=DEFAULT_SSE_URL,
        help="AMBOSS MCP SSE endpoint (default: %(default)s). Use an empty string to skip.",
    )
    parser.add_argument(
        "--no-sse",
        action="store_true",
        help="Skip the SSE connectivity check.",
    )
    parser.add_argument(
        "--tool",
        type=str,
        default=None,
        help="Optional tool to invoke after listing the catalogue (e.g. list_all_articles).",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=("de", "en"),
        help="Override the language argument when calling a tool.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter an interactive prompt to call MCP tools after the health checks.",
    )
    return parser.parse_args(argv)


def _run_cli_interactive_loop(
    *,
    tools: Sequence[Dict[str, Any]],
    http_url: str,
    api_key: str,
    timeout: float,
    default_language: Optional[str],
    reporter: Reporter,
) -> None:
    """Provide a simple REPL to call MCP tools from the terminal."""

    name_to_tool = {tool.get("name", ""): tool for tool in tools}
    reporter.info(
        "Entering interactive mode. Press Enter without typing a tool name to exit."
    )
    while True:
        try:
            tool_name = input("Tool to call (blank to quit): ").strip()
        except EOFError:
            reporter.info("EOF received – exiting interactive mode.")
            break

        if not tool_name:
            reporter.info("Interactive mode finished.")
            break

        if tool_name not in name_to_tool:
            available = ", ".join(sorted(name for name in name_to_tool if name))
            reporter.info(
                f"Unknown tool '{tool_name}'. Available tools: {available}"
            )
            continue

        tool = name_to_tool[tool_name]
        default_args: Dict[str, Any] = {}
        if default_language:
            default_args.setdefault("language", default_language)
        primary_argument = _extract_primary_argument_name(tool)

        reporter.info(
            "Provide arguments (JSON or key=value pairs, leave empty for {}):".format(
                json.dumps(default_args) if default_args else "{}"
            )
        )
        raw_args = input("Arguments: ").strip()
        if raw_args:
            try:
                arguments = _parse_arguments_input(
                    raw_args, fallback_key=primary_argument
                )
            except ValueError as exc:
                reporter.info(f"Invalid arguments: {exc}")
                continue
        else:
            arguments = default_args

        if default_language:
            arguments.setdefault("language", default_language)

        result = call_tool(
            http_url,
            api_key,
            name=tool_name,
            arguments=arguments or None,
            timeout=timeout,
        )
        reporter.json(result)


def _render_streamlit_tool_invocation(
    *,
    tools: Sequence[Dict[str, Any]],
    http_url: str,
    api_key: str,
    timeout: float,
    default_language: Optional[str],
) -> None:
    """Render interactive controls in Streamlit to call MCP tools."""

    if st is None:
        return

    st.subheader("Interaktive MCP-Tool-Abfrage")
    tool_names = [tool.get("name", "") for tool in tools if tool.get("name")]
    if not tool_names:
        st.info("Keine Tools verfügbar, Interaktion übersprungen.")
        return

    selected_tool = st.selectbox("Tool auswählen", tool_names)
    tool = next((t for t in tools if t.get("name") == selected_tool), None)
    if tool:
        _render_tool_description(tool)

    default_lang = default_language or "de"
    primary_argument = _extract_primary_argument_name(tool or {})

    if primary_argument:
        st.caption(
            "Bitte geben Sie entweder gültiges JSON **oder** einen Suchbegriff ein. "
            "Freitext wird automatisch als Argument '{arg}' übernommen.".format(
                arg=primary_argument
            )
        )
    else:
        st.caption(
            "Argumente können als JSON **oder** als einfache Zeilen wie "
            "`schlüssel=wert` eingegeben werden. Mehrere Werte bitte durch Zeilenumbrüche "
            "oder Kommas trennen."
        )

    st.caption(f"Die Sprache wird automatisch auf '{default_lang}' gesetzt.")

    placeholder = "Suchbegriff eingeben" if primary_argument else "schlüssel=wert"
    args_text = st.text_area(
        "Tool-Argumente",
        value="",
        placeholder=placeholder,
    )

    if st.button("Tool ausführen"):
        try:
            parsed_args = _parse_arguments_input(
                args_text, fallback_key=primary_argument
            )
        except ValueError as exc:
            st.error(f"Ungültige Eingabe: {exc}")
            return

        arguments: Dict[str, Any] = {}
        if default_lang:
            arguments["language"] = default_lang
        arguments.update(parsed_args)

        try:
            result = call_tool(
                http_url,
                api_key,
                name=selected_tool,
                arguments=arguments or None,
                timeout=timeout,
            )
        except MCPConnectionError as exc:
            st.error(str(exc))
            return

        st.success("Tool erfolgreich ausgeführt.")
        _render_streamlit_result(result)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    api_key = args.token or load_amboss_token(args.secrets_path)
    http_url = (args.http_url or "").strip()
    sse_url = (args.sse_url or "").strip()
    timeout = float(args.timeout)

    if not http_url:
        raise MCPConnectionError("An MCP HTTP endpoint must be provided via --http-url.")

    language = args.language

    use_streamlit = _is_running_with_streamlit()
    reporter: Reporter = StreamlitReporter() if use_streamlit else ConsoleReporter()

    reporter.section("MCP HTTP connectivity test")
    tools = list_tools(http_url, api_key, timeout)
    reporter.info(f"Retrieved {len(tools)} tools from the MCP server.")
    for tool in tools:
        name = tool.get("name", "<unknown>")
        description = tool.get("description", "")
        reporter.bullet(name, description)

    if args.tool:
        reporter.section(f"Invoking MCP tool '{args.tool}'")
        arguments: Dict[str, Any] = {}
        if language:
            arguments["language"] = language
        result = call_tool(
            http_url,
            api_key,
            name=args.tool,
            arguments=arguments or None,
            timeout=timeout,
        )
        reporter.json(result)

    if args.interactive and not use_streamlit:
        _run_cli_interactive_loop(
            tools=tools,
            http_url=http_url,
            api_key=api_key,
            timeout=timeout,
            default_language=language,
            reporter=reporter,
        )

    if not args.no_sse and sse_url:
        reporter.section("MCP SSE connectivity test")
        check_sse_endpoint(sse_url, api_key, timeout, reporter)
    elif not sse_url:
        reporter.info("(No SSE URL configured – skipping SSE check.)")

    if use_streamlit:
        _render_streamlit_tool_invocation(
            tools=tools,
            http_url=http_url,
            api_key=api_key,
            timeout=timeout,
            default_language=language,
        )

    reporter.info("All MCP checks completed successfully.")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    try:
        raise SystemExit(main())
    except MCPConnectionError as exc:
        print(f"MCP connectivity test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
