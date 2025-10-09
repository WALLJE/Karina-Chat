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
application.

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
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

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


def build_headers(api_key: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Create the HTTP headers required for MCP requests."""

    headers = {"Authorization": f"Bearer {api_key}"}
    if extra:
        headers.update(extra)
    return headers


def check_sse_endpoint(url: str, api_key: str, timeout: float) -> None:
    """Attempt to open the SSE stream and print the first line if available."""

    print(f"Connecting to SSE endpoint: {url}")
    headers = build_headers(api_key, {"Accept": "text/event-stream"})

    try:
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                raise MCPConnectionError(
                    f"SSE endpoint returned status {resp.status_code}: {resp.text.strip()}"
                )

            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    print(f"First SSE event line: {line}")
                    break
            else:
                print("SSE connection established but no events were received (yet).")
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
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    api_key = args.token or load_amboss_token(args.secrets_path)
    http_url = (args.http_url or "").strip()
    sse_url = (args.sse_url or "").strip()
    timeout = float(args.timeout)

    if not http_url:
        raise MCPConnectionError("An MCP HTTP endpoint must be provided via --http-url.")

    language = args.language

    print("=== MCP HTTP connectivity test ===")
    tools = list_tools(http_url, api_key, timeout)
    print(f"Retrieved {len(tools)} tools from the MCP server.")
    for tool in tools:
        name = tool.get("name", "<unknown>")
        description = tool.get("description", "")
        print(f"- {name}: {description}")

    if args.tool:
        print(f"\n=== Invoking MCP tool '{args.tool}' ===")
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
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if not args.no_sse and sse_url:
        print("\n=== MCP SSE connectivity test ===")
        check_sse_endpoint(sse_url, api_key, timeout)
    elif not sse_url:
        print("\n(No SSE URL configured – skipping SSE check.)")

    print("\nAll MCP checks completed successfully.")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    try:
        raise SystemExit(main())
    except MCPConnectionError as exc:
        print(f"MCP connectivity test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
