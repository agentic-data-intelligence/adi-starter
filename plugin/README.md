<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# ADI — plugin bundle

**Status: Closed Beta.** Starter Edition is in Closed Beta: access is by invitation, and you should expect changes and fixes while the Beta runs. See the [documentation](https://docs.agentic-data.com) for setup and current limitations.

One plugin bundle, consumed by every plugin-based host: **Claude Code (+ Cowork)**,
**Cursor**, and **Codex**. It ships the two ADI skills (`adi-querying`, `adi-authoring`) plus the
ADI MCP server. Edit the skill files under `skills/` directly; the per-host manifests
and the shared `mcp.json` are hand-maintained.

## Layout

```text
plugin/
├── skills/{adi-querying,adi-authoring}/   SKILL.md (+ references / examples / schemas)
├── plugin.json                  vendor-neutral Agent Plugins 1.0.0 manifest
├── mcp.json                     the one MCP config (Agent Plugins format) — OAuth, no credentials
├── .claude-plugin/plugin.json   Claude Code manifest (mcpServers → ./mcp.json)
├── .codex-plugin/plugin.json    Codex manifest (declares skills + mcpServers → ./mcp.json)
├── .cursor-plugin/plugin.json   Cursor manifest (mcpServers → ./mcp.json)
└── assets/adi_logo.png          plugin logo
```

Each host reads its own manifest directory and ignores the others. An
[Agent Plugins](https://agent-plugins.org) host reads the root `plugin.json` and `mcp.json`.

There is one MCP config, `mcp.json`, in the Agent Plugins format: a `$schema` key and
`"type": "streamable-http"`. Agent Plugins fixes that file name and allows no other `type`
for a remote server; Claude Code accepts `streamable-http` as an alias of its `http`. Every
vendor manifest points `mcpServers` at `./mcp.json`, so do not add a `.mcp.json`: two MCP
configs can drift apart. Tested with Claude Code 2.1.304, Codex CLI
0.142.0 and Claude Cowork; not yet tested in Cursor.

## No nested `agents/` under `skills/<name>/`

Codex supports an **optional** per-skill `agents/openai.yaml` (UI appearance +
implicit-invocation policy + a tool-dependency declaration) that, per the
[Codex skills spec](https://developers.openai.com/codex/skills), _must_ live inside the
skill directory (`skills/<name>/agents/openai.yaml`). This unified bundle **cannot ship
it**: Claude Code auto-discovers plugin skills from `skills/<name>/SKILL.md` and treats a
nested `skills/<name>/agents/` as an illegal layout — plugin agents belong at
`<plugin-root>/agents/`, not inside `skills/` (see the Claude Code
[plugins reference](https://code.claude.com/docs/en/plugins-reference#file-locations-reference)) —
so its mere presence makes Claude Code **silently register 0 skills** for the whole plugin.

Since this bundle is Claude-Code-first and the manifest is optional for Codex, we omit it.
**Codex is unaffected in substance:** both skills still load (from the `.codex-plugin`
`skills` list + each `SKILL.md`), and the `adi` MCP server is fully declared in
`mcp.json` and `.codex-plugin/plugin.json`. Only the optional per-skill niceties
(custom display name / default prompt, `allow_implicit_invocation`) are dropped in the
Codex UI. Full Codex UI parity would require a **separate Codex-only bundle** — the
manifest cannot coexist with Claude in one directory. Do not add a nested `agents/` (or
any other subdir) under `skills/<name>/`.

## Auth

The MCP server uses OAuth: the hosted ADI service opens a Zitadel browser login on first
connect, so `mcp.json` ships with no credentials and needs no configuration.

To start the sign-in in Claude Code, type `/mcp` in a session, select `adi` and authenticate. Run `codex mcp login adi` in Codex, or approve the prompt Cursor shows when the server first connects. Then complete the login in your browser. In Cowork you connect from the plugin's Connectors tab instead (see Using ADI in Claude Cowork in [Getting Started](https://docs.agentic-data.com/docs/starter-edition/getting-started)).

If a Claude Code session that was already open when you signed in does not show the ADI tools, type `/mcp` in that session too, select `adi` and authenticate.

## Install

- **Claude Code** — add the marketplace at the repo root, then install `adi`:
  `/plugin marketplace add agentic-data-intelligence/adi-starter`
- **Claude Cowork:** in the Claude desktop app, open **Customize > Plugins**, select **Add > Add marketplace**, enter `https://github.com/agentic-data-intelligence/adi-starter`, add the ADI plugin, then connect the `adi` connector from the plugin's **Connectors** tab. If you use Claude Cowork and Claude Code, install in the app. Full steps: [Getting Started, Using ADI in Claude Cowork](https://docs.agentic-data.com/docs/starter-edition/getting-started).
- **Codex** — `codex plugin marketplace add agentic-data-intelligence/adi-starter`,
  then `codex plugin add adi@adi`.
- **Cursor** — clone the repo, then copy this directory (not a symlink: Cursor skips
  symlinks in `~/.cursor/plugins/local` that point elsewhere on disk). From the repo
  root, removing any symlink left by earlier install instructions first:

  ```bash
  if [ -L ~/.cursor/plugins/local/adi ]; then rm ~/.cursor/plugins/local/adi; fi
  mkdir -p ~/.cursor/plugins/local/adi && cp -R plugin/. ~/.cursor/plugins/local/adi/
  ```

  Restart Cursor or run **Developer: Reload Window**. On Teams and Enterprise plans, an
  admin controls whether local plugins load, with **Allow Local Plugin Imports**
  (Dashboard > Settings > Security & Identity > Marketplace and Plugins). It is off by
  default on Enterprise. To update: `git pull`, `rm -rf ~/.cursor/plugins/local/adi`, re-copy,
  reload.

MCP client setup and troubleshooting: [docs/mcp-clients.md](../docs/mcp-clients.md).
