<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# MCP client configs (ADI hosted)

The `adi` plugin ships the MCP server config in [`plugin/mcp.json`](../plugin/mcp.json), in the
[Agent Plugins](https://agent-plugins.org) format that every host below reads.
Installing the plugin registers it automatically (in Claude Cowork you also add the connector; see below). Use the notes below to configure a
client by hand, or if tools do not register after install.

`mcp.json` carries no credentials, so every client uses the hosted service's
OAuth flow — a Zitadel browser login on first connect, with nothing to configure:

- **Claude Code:** type `/mcp` in a session, select `adi` and authenticate, then complete
  the login in your browser. If a Claude Code session that was already open when you
  signed in does not show the ADI tools, type `/mcp` in that session too, select `adi`
  and authenticate. If you installed in the Claude desktop app and added its connector
  there: in our tests on a Team plan, the terminal's `/mcp` listed that `adi` connector as
  disabled; select it and choose **Enable**.
- **Claude Cowork:** connect from the plugin's Connectors tab, opened from Cowork, instead (see Using ADI in Claude
  Cowork in [Getting Started](https://docs.agentic-data.com/docs/starter-edition/getting-started)).
- **Cursor:** if the `adi` server shows **Needs Authentication**, select **Authenticate**,
  then complete the login in your browser.
- **Codex:** `auth` defaults to `oauth` for HTTP servers — run `codex mcp login adi`
  (Codex opens a local callback listener). In the Codex app, the sign-in completes in your
  browser.

| Client        | File                                  | Where it goes                                                                                                                                                                        |
| ------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Claude Code   | [plugin/mcp.json](../plugin/mcp.json) | Bundled in the `adi` plugin (`/plugin install adi`). Uses OAuth (Zitadel browser login): no credentials to configure (sign in with `/mcp` in a session).                             |
| Claude Cowork | [plugin/mcp.json](../plugin/mcp.json) | Bundled in the `adi` plugin (**Customize > Plugins**). Installing does not add the connector: add and connect `adi` from the plugin's **Connectors** tab, opened from Cowork.                            |
| Cursor        | [plugin/mcp.json](../plugin/mcp.json) | Cursor's manifest points `mcpServers` at this file; or merge it into `~/.cursor/mcp.json` under `mcpServers`.                                                                        |
| Codex         | [plugin/mcp.json](../plugin/mcp.json) | Bundled in the `adi` plugin (install via `.agents/plugins/marketplace.json`). OAuth (`codex mcp login adi`); for a loose install, add `[mcp_servers.adi]` to `~/.codex/config.toml`. |

**Claude Code:** use `"type": "streamable-http"` (or its Claude Code name, `"http"`), not
`"type": "url"`. Restart after save; approve trust if prompted.

**Any other MCP client.** Point it at the server URL in `plugin/mcp.json`. The configuration is a small JSON block naming the server and its URL, for example (some clients call this transport `"http"`; check yours):

```json
{
  "mcpServers": {
    "adi": {
      "type": "streamable-http",
      "url": "<the URL in plugin/mcp.json>"
    }
  }
}
```

Where this file goes depends on your client (for Claude Code, `.mcp.json` in your project root; for Cursor, `.cursor/mcp.json` in your project or `~/.cursor/mcp.json`); check your client's own MCP documentation for the exact location. On first connection you sign in with, or create, a Zitadel account.

---

## Verification (`curl`)

The normal way to verify is through the client itself: check its `/mcp` view after
signing in. `curl` can't run the browser OAuth flow, but two checks are still
useful:

**Endpoint liveness (no credentials).** An unauthenticated request must answer
`401` with a `WWW-Authenticate` header pointing at the OAuth metadata — that
confirms the endpoint is up and the OAuth challenge works:

```bash
curl -si -X POST https://mcp-starter.agentic-data.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | head -5
```

**Authenticated call.** Paste a `Bearer` token from an OAuth session into an
`Authorization` header:

```bash
curl -X POST https://mcp-starter.agentic-data.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer ${ADI_OAUTH_TOKEN}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | grep "^data:" | head -1 | sed 's/^data: //' | python3 -m json.tool
```

A good response lists `adi.get_capabilities`, `adi.get_authoring_spec`,
`adi.generate_query`, `adi.validate`, and related tooling. A `401` means the
token is missing, expired, or revoked — re-run the client's MCP login.

---

## HTTP fallback (from code)

If native MCP registration fails, call the endpoint directly with a `Bearer` token
from an OAuth session (this path does not perform the browser flow itself):

```python
import os, requests, json, time

API_URL = "https://mcp-starter.agentic-data.com/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {os.environ['ADI_OAUTH_TOKEN']}"
}

def adi_call(tool, arguments):
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments}
    }
    resp = requests.post(API_URL, json=payload, headers=HEADERS)
    for line in resp.text.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])["result"]

time.sleep(0.4)
capabilities = adi_call("adi.get_capabilities", {})
print(capabilities)
```

This does not replace MCP tool discovery in the host; it is a last-resort way to verify
the endpoint and call tools from code.

**Python SSL note:** use the `requests` library (with `certifi`), not the built-in
`urllib` — Python 3.13's `urllib` can fail with `SSL: CERTIFICATE_VERIFY_FAILED` against
the ADI server, while `requests` handles it automatically (`pip install requests certifi`).
