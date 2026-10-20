<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# Contributing to ADI Starter

Contributions are welcome. Please read the guidelines below.

## Before you contribute

1. **CLA**: You must sign the [Contributor License Agreement (CLA)](CLA.md) before your contribution can be accepted.
2. **Individual contributors**: Include "I agree to the CLA" in your pull request.
3. **Corporate contributors**: Contact <contributions@agentic-data.com> to arrange a corporate CLA.

## Editing the skills

The two skills live under [`plugin/skills/`](plugin/skills/):

- `plugin/skills/adi-querying/` — `SKILL.md` plus `references/` and `examples/`
- `plugin/skills/adi-authoring/` — `SKILL.md` plus the ADI Contract v1 `schemas/`

Edit these files directly. Keep the YAML frontmatter valid — `name` must match the
folder name, and the shipped `compatibility` string and `metadata.mcp_tools` /
`metadata.mcp_tools_self_hosted` lists should stay accurate. Custom keys belong under
`metadata` (string values): the Agent Skills spec, `skills-ref validate` and claude.ai /
Skills API uploads reject unknown top-level frontmatter keys.

**Do not add a nested `agents/` (or any other subdirectory) under
`plugin/skills/<name>/`.** Claude Code treats a nested `skills/<name>/agents/` as an
illegal layout and silently registers **0 skills** for the whole plugin. See
[plugin/README.md](plugin/README.md) for the full rationale.

## Hand-maintained files

These are not skill content — change them deliberately and keep them consistent:

- Per-host plugin manifests under `plugin/` (`.claude-plugin/`, `.codex-plugin/`,
  `.cursor-plugin/`), each pointing `mcpServers` at `./mcp.json`.
- The vendor-neutral [Agent Plugins 1.0.0](https://agent-plugins.org) files `plugin/plugin.json`
  and `plugin/mcp.json`, the only MCP config. Their schemas are closed: `plugin.json` takes
  only `$schema`, `name`, `version`, `description`, `author`, `homepage`, `repository`,
  `license`, `keywords` and `extensions`, and `mcp.json` takes `$schema` and `mcpServers`, with
  `"type": "streamable-http"` (not `"http"`, which Agent Plugins rejects).
- The repo-root marketplace manifests (`.claude-plugin/`, `.cursor-plugin/`,
  `.agents/plugins/`) — all three point their plugin `source` at `./plugin`.
- `docs/mcp-clients.md`.

When bumping the plugin version, update it in the three `plugin/.*-plugin/plugin.json` manifests,
`plugin/plugin.json`, and in the `.claude-plugin/` and `.cursor-plugin/` root `marketplace.json` files (the
`.agents/plugins/` one has no version field).

## Process

1. Open an issue to discuss substantial changes.
2. Fork the repository and create a branch.
3. Make focused commits with clear messages.
4. Submit a pull request referencing any related issues.

## Questions

For contribution-related questions: <contributions@agentic-data.com>
