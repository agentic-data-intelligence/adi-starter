<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# ADI Starter

**Contract-governed analytics for AI agents.** This repository packages the ADI skills
and the ADI MCP server as a single plugin you can install into Claude Code, Codex, or
Cursor — or drop the skills into any agent that supports [Agent Skills](https://agentskills.io).

Two skills ship together:

- **`adi-querying`** — turns metric / KPI / dimension questions into deterministic,
  contract-governed SQL via the ADI MCP tools (`adi.get_capabilities` →
  `adi.generate_query`). No natural language ever goes on the wire; every query is
  generated against your ADI contract. The hosted Beta endpoint is trust tier T1 and
  generation-only: it returns the SQL for you to run against your own warehouse. On an
  execution tier (a server that reports `features.execute_sql`), queries can also run
  through `adi.execute_sql`, and that SQL is cryptographically signed.
- **`adi-authoring`** — authors an ADI Contract v1 YAML bundle (contract, entities,
  metrics, vocabulary, optional policies / rules) from live database metadata, validated
  against the shipped JSON Schemas.

Both skills are **domain-agnostic**: they work with any ADI contract served by an ADI
MCP endpoint.

## Install as a plugin

The plugin registers **both skills and the ADI MCP server** in one step.

### Claude Code

```text
/plugin marketplace add agentic-data-intelligence/adi-starter
/plugin install adi
```

Verify with `/skills` and `/mcp`.

### Codex

```bash
codex plugin marketplace add agentic-data-intelligence/adi-starter
# then, in Codex, install the `adi` plugin and restart; verify with /skills and /mcp
```

### Cursor

Copy `plugin/` into Cursor's local plugin folder. Use a real copy: Cursor skips a
symlink in `~/.cursor/plugins/local` that points elsewhere on disk.

```bash
git clone https://github.com/agentic-data-intelligence/adi-starter.git
cd adi-starter
# remove a symlink left by earlier install instructions
if [ -L ~/.cursor/plugins/local/adi ]; then rm ~/.cursor/plugins/local/adi; fi
mkdir -p ~/.cursor/plugins/local/adi
cp -R plugin/. ~/.cursor/plugins/local/adi/
```

Restart Cursor, or run **Developer: Reload Window**, then open **Customize** and
confirm the `adi` skills and MCP server are listed. On Teams and Enterprise, local
plugins load only if an admin has enabled **Allow Local Plugin Imports** (off by default
on Enterprise).

The copy doesn't follow the repository. To update, pull and re-copy, then reload:

```bash
git pull
rm -rf ~/.cursor/plugins/local/adi
mkdir -p ~/.cursor/plugins/local/adi
cp -R plugin/. ~/.cursor/plugins/local/adi/
```

Full per-host notes: [plugin/README.md](plugin/README.md).

## Use as a skills source

The two skills are standard Agent Skills, so the
[`skills`](https://github.com/vercel-labs/skills) CLI installs them into any supported
agent straight from this repo — no clone:

```bash
npx skills add https://github.com/agentic-data-intelligence/adi-starter/tree/main/plugin/skills/adi-querying
npx skills add https://github.com/agentic-data-intelligence/adi-starter/tree/main/plugin/skills/adi-authoring

# target a specific agent, install globally, non-interactively
npx skills add <same-url> -a claude-code -g -y
```

Or copy the folders by hand into your agent's skills directory (each contains a
`SKILL.md` at its root):

```bash
mkdir -p ~/.claude/skills
cp -r plugin/skills/adi-querying plugin/skills/adi-authoring ~/.claude/skills/
```

`npx skills add` / a manual copy installs only the `SKILL.md` folder — configure the ADI
MCP server separately (see [docs/mcp-clients.md](docs/mcp-clients.md)).

## Authentication

The ADI MCP server uses OAuth: `.mcp.json` ships with no credentials, so the
hosted service opens a Zitadel browser login on first connect — nothing to configure.
Run `claude mcp login adi` (Claude Code) or `codex mcp login adi` (Codex), or approve
Cursor's in-app prompt, then complete the login in the browser.

Details and per-client config: [docs/mcp-clients.md](docs/mcp-clients.md).

## Layout

```text
adi-starter/
├── .claude-plugin/marketplace.json   Claude Code marketplace manifest → ./plugin
├── .cursor-plugin/marketplace.json   Cursor marketplace manifest → ./plugin
├── .agents/plugins/marketplace.json  Codex marketplace manifest → ./plugin
├── plugin/                           the unified plugin bundle (skills + MCP)
│   ├── skills/{adi-querying,adi-authoring}/
│   ├── .mcp.json
│   ├── .claude-plugin/ .codex-plugin/ .cursor-plugin/ .plugin/
│   └── assets/adi_logo.png
└── docs/mcp-clients.md               MCP client configs + HTTP fallback
```

## Documentation

- **Human readable docs:** <https://docs.agentic-data.com>
- **Machine-readable docs (for AI agents):** <https://docs.agentic-data.com/llms.txt>

The `llms.txt` file is a structured index pointing to plain-text (`.txt`) versions of every documentation page — use this if you're an agent or tool reading the docs programmatically. A concatenated single-file version of all docs is also available at [`llms-full.txt`](https://docs.agentic-data.com/llms-full.txt).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
