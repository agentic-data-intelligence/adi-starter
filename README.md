<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# ADI Starter

**Status: Closed Beta.** Starter Edition is in Closed Beta: access is by invitation, and you should expect changes and fixes while the Beta runs. See the [documentation](https://docs.agentic-data.com) for setup and current limitations.

**Contract-governed analytics for AI agents.** This repository packages the ADI skills
and the ADI MCP server as a single plugin you can install into Claude Code (+ Cowork),
Cursor, and Codex, or drop the skills into any agent that supports
[Agent Skills](https://agentskills.io).

Two skills ship together:

- **`adi-querying`** — turns metric / KPI / dimension questions into deterministic,
  contract-governed SQL via the ADI MCP tools (`adi.get_capabilities` →
  `adi.generate_query`). No natural language ever goes on the wire; every query is
  generated against your ADI contract. The hosted Beta endpoint is trust tier `t1` and
  generation-only: it returns the SQL for you to run against your own warehouse. On an
  execution tier (a server that reports `features.execute_sql`), queries can also run
  through `adi.execute_sql`, and that SQL is cryptographically signed.
- **`adi-authoring`** — authors an ADI Contract v1 YAML bundle (contract, entities,
  metrics, vocabulary, optional policies / rules) from live database metadata, validated
  against the shipped JSON Schemas.

Both skills are **domain-agnostic**: they work with any ADI contract served by an ADI
MCP endpoint.

## Install as a plugin

The plugin registers **both skills and the ADI MCP server** in one step (in Claude Cowork you also add the connector, as below).

### Claude Code

```text
/plugin marketplace add agentic-data-intelligence/adi-starter
/plugin install adi
```

Verify with `/skills` and `/mcp`.

### Claude Cowork

In the Claude desktop app, open **Customize > Plugins**, select **Add > Add marketplace**, enter `https://github.com/agentic-data-intelligence/adi-starter`, then add the ADI plugin. Then open the plugin's **Connectors** tab to add and connect the `adi` connector; on Team and Enterprise plans an Owner adds it for the organisation. If you are not an Owner, ask your admin to add it, then connect it with your own account. Full steps: [Getting Started, Using ADI in Claude Cowork](https://docs.agentic-data.com/docs/starter-edition/getting-started).

Cowork, in the Claude desktop app, uses the same ADI plugin as Claude Code: there is one Claude plugin, not one for each. If you use both, install ADI in the app. A plugin added there is saved to your Claude account, so it is available in Cowork and in Claude Code, both in the desktop app and on the command line. A plugin installed from the Claude Code command line is available in Claude Code only, not in Cowork. Installing in both places can load more than one copy of the ADI tools, and it is not obvious which one your agent is calling.

### Codex

```bash
codex plugin marketplace add agentic-data-intelligence/adi-starter
codex plugin add adi@adi
# then restart Codex; verify with /skills and /mcp
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
confirm the `adi` skills and MCP server are listed. On Teams and Enterprise plans, an
admin controls whether local plugins load, with **Allow Local Plugin Imports**
(Dashboard > Settings > Security & Identity > Marketplace and Plugins). It is off by
default on Enterprise.

The copy doesn't follow the repository. To update, pull and re-copy, then reload:

```bash
git pull
rm -rf ~/.cursor/plugins/local/adi
mkdir -p ~/.cursor/plugins/local/adi
cp -R plugin/. ~/.cursor/plugins/local/adi/
```

### Other agents

For OpenClaw, Manus, and any other coding agents that support either the [Agent Plugins Specification](https://agent-plugins.org) or the Agent Skills Specification: copy the two Skill folders (`adi-querying` and `adi-authoring`, in `plugin/skills/`) into your agent's skills directory, then configure the ADI MCP server as shown in [docs/mcp-clients.md](docs/mcp-clients.md). An Agent Plugins host can load the `plugin/` folder directly: its manifest is `plugin/plugin.json` and its MCP configuration is `plugin/mcp.json`. To install the Skills with the `skills` CLI instead of copying them, see [Use as a skills source](#use-as-a-skills-source).

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

The ADI MCP server uses OAuth: `mcp.json` ships with no credentials, so the
hosted service opens a Zitadel browser login on first connect — nothing to configure.
To start the sign-in in Claude Code, type `/mcp` in a session, select `adi` and authenticate. Run `codex mcp login adi` in Codex, or approve the prompt Cursor shows when the server first connects. Then complete the login in your browser. In Cowork you connect from the plugin's Connectors tab instead (see Using ADI in Claude Cowork in [Getting Started](https://docs.agentic-data.com/docs/starter-edition/getting-started)).

If a Claude Code session that was already open when you signed in does not show the ADI tools, type `/mcp` in that session too, select `adi` and authenticate.

Details and per-client config: [docs/mcp-clients.md](docs/mcp-clients.md).

## Layout

```text
adi-starter/
├── .claude-plugin/marketplace.json   Claude Code marketplace manifest → ./plugin
├── .cursor-plugin/marketplace.json   Cursor marketplace manifest → ./plugin
├── .agents/plugins/marketplace.json  Codex marketplace manifest → ./plugin
├── plugin/                           the unified plugin bundle (skills + MCP)
│   ├── skills/{adi-querying,adi-authoring}/
│   ├── plugin.json mcp.json          Agent Plugins 1.0.0 manifest + the one MCP config
│   ├── .claude-plugin/ .codex-plugin/ .cursor-plugin/
│   └── assets/adi_logo.png
└── docs/mcp-clients.md               MCP client configs + HTTP fallback
```

## Documentation

- **Human readable docs:** <https://docs.agentic-data.com>
- **Machine-readable docs (for AI agents):** <https://docs.agentic-data.com/llms.txt>

The `llms.txt` file is a structured index pointing to plain-text (`.txt`) versions of every documentation page — use this if you're an agent or tool reading the docs programmatically. A concatenated single-file version of all docs is also available at [`llms-full.txt`](https://docs.agentic-data.com/llms-full.txt).

## Getting help

If this repository does not answer your question, check the [documentation](https://docs.agentic-data.com) first. If that does not solve it, the [Support and Security page](https://docs.agentic-data.com/docs/reference/support) explains how to contact us, and how to report a security issue privately.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
