---
name: adi-querying
description: >
  Generates contract-governed analytical SQL via ADI MCP tools using
  `query_request` v1. Use when users ask metric/KPI/dimension questions,
  including everyday requests such as a daily report, revenue or orders.
  Build a structured request and call `adi.generate_query`; do not ask ADI
  to parse natural language on your behalf. When the server allows it
  (`features.execute_sql` from `adi.get_capabilities`), call `adi.execute_sql` **only**
  with SQL + signature from the same successful `generate_query` — unsigned queries are
  never executable via MCP.
license: Apache-2.0
compatibility: Claude Code, Claude Cowork, Cursor, OpenClaw, Manus, Codex
metadata:
  author: agentic-data-intelligence
  version: "2.8.0"
  short-description: Answer metric and KPI questions about business data with contract-governed SQL from ADI
  mcp_tools: adi.get_capabilities adi.generate_query adi.validate
  mcp_tools_self_hosted: adi.execute_sql
---

# ADI querying

## Quick start

1. Call **`adi.get_capabilities`** first. Note **`features.execute_sql`**, **`features.core_tools`** (for **`generate_query`** / **`validate`**), and whether **`adi.execute_sql`** appears in **`enabled_tools`**.
   - **Authorization check (before anything else).** If the response has an **`authorization`** block and **`authorization.status`** is **`"pending_approval"`** (or, on older servers without `status`, **`authorization.query_role_granted`** is **`false`**), you are authenticated but **not approved**. Lead with that fact — relay **`authorization.message`** verbatim when present (it names the exact role and the correct retry guidance); otherwise say: _"Your ADI access is pending approval — an admin needs to grant you the query role; once granted, just ask again (no re-login)."_ Then **stop** — do not discover a contract, build a request, or call `generate_query`, and do **not** present role flags or `enabled_tools` as capabilities the user "has" while approval is pending. You may **offer to re-check periodically** (re-call `adi.get_capabilities` on the user's say-so) and continue automatically the moment `status` flips to `approved` — no re-login needed — so the user isn't left manually polling. (No `authorization` block means auth isn't role-gated here — proceed normally.)
   - If `adi.validate` or `adi.generate_query` returns an error with the code `insufficient_role`, the account's ADI access is still pending approval. Tell the user so, as the error message says. Then stop. It is an error, not a refusal, so it is not in the refusal codes.
2. Build a `query_request` v1 object.
3. Call **`adi.generate_query`** with `query_request=…` and `contract=…` (see **Providing the contract** below), plus `row_limit` when the server requires it.
4. On **`ok=true`**:
   - If **`warnings`** is non-empty, surface them in the user-facing answer when policy-safe (contracts may attach semantic or governance notices).
   - **MCP execution is only for signed output.** Call **`adi.execute_sql`** only when execution is enabled (step 1), **`query.signature`** is present, and **`contract_hash`** is on the response — pass **`query.sql`**, **`query.dialect`**, **`contract_hash`**, and **`query.signature`** together. Without a **`signature`**, **`adi.execute_sql`** must not be called; unsigned SQL is not runnable through MCP (use **`query.sql`** off-platform if needed).
   - After a successful **`adi.execute_sql`**, use **`result.rows`** / **`result.columns`** for tabular data. Always incorporate **`query.provenance`** and **`query.explanation`** from the same **`generate_query`** response in user-facing answers (**`execute_sql`** does not return those fields).
   - If execution is unavailable or there is **no** **`signature`** (the Starter/**T1** posture — **`features.execute_sql`** is `false` and `generate_query` returns no **`query.signature`**), the SQL is **not** run through MCP. Take **`query.sql`** with **`query.provenance`** / **`query.explanation`** and either run it **client-side with a database client or connection that is already installed and configured in this environment**, or **present it to the user to run** (see **[Client-side execution (T1)](#client-side-execution-t1)** below). Never pipe raw SQL into **`adi.execute_sql`** without a valid **`signature`**.
5. On refusal, use **`refusal.code`**, **`refusal.suggestion`**, and **`refusal.details`** to recover (see [references/refusal_codes.md](references/refusal_codes.md)).

## Server-side execution checklist

**Rule:** **`adi.execute_sql` executes only ADI-signed SQL.** Unsigned queries are **not** executable via MCP; the server rejects them even if `execute_sql` is enabled.

Use **`adi.execute_sql`** only when **`features.execute_sql`** is true **and** **`enabled_tools`** includes **`adi.execute_sql`** **and** **`generate_query`** returned **`query.signature`** (and **`contract_hash`**). If **`signature`** is missing, skip **`adi.execute_sql`** entirely.

**`adi.execute_sql` response shape** differs from `generate_query` — it has **no** `refusal`. On success: `{ok: true, result: {rows, columns, row_count}}`. On failure: `{ok: false, error: {code, message}}` (codes include `execution_failed`, `unsafe_sql_denied`, `feature_disabled`, `auth_required`, `request_malformed`). Read `error` here, not `refusal`.

## Client-side execution (T1)

At Starter (**T1**) the ADI MCP **only generates and validates SQL**: **`features.execute_sql`** is `false`, `adi.execute_sql` is not in **`enabled_tools`**, and `generate_query` returns **no `query.signature`**. There is no ADI-side database and no warehouse MCP tool, so the generated **`query.sql`** must be run **against the user's own warehouse, client-side, with a client already set up in this environment or one the user agrees to install**, or handed to the user to run. This is expected; it is not a failure and not "no access to your warehouse."

- **Run it with a client that is already set up.** ADI does not ship or manage a client-side executor — it hands you **`query.sql`**. Run it through whatever warehouse connection the environment already provides (the user's own SQL client, a notebook/JDBC connection, native database tooling). Use the returned rows for the tabular answer, and always incorporate **`query.provenance`** / **`query.explanation`** from the same `generate_query` response.
- **Ask before installing anything to run it.** If no client or connection is already set up, do not install, download or update a driver, library, command-line tool or package, or create a virtual environment for one, until the user agrees: say what you want to install and why, and wait for a yes in the conversation. A permission setting that approves commands automatically is not that agreement. If the user says no, present the SQL instead (see **Or present it**).
- **Run the SQL ADI returned, never a retyped copy.** Save **`query.sql`** to a file exactly as returned, and run that saved file. Do not retype, reformat or edit it first; if you need a wrapper (see **Coarser time grains**), keep the saved query byte-for-byte unchanged inside it.
- **Or present it.** If you cannot run SQL in this environment, show **`query.sql`** alongside **`query.provenance`** and **`query.explanation`** so the user can run it themselves and understand what it does.
- **Guardrails (unchanged).** **`adi.execute_sql`** is still **never** called without a valid **`signature`** — unsigned, generator-produced SQL runs only on the user's own warehouse, never through ADI-signed execution. Do **not** read credential stores, keychains, session cookies, or tokens yourself; use only a connection the user has already configured.

## Providing the contract

`adi.generate_query` needs the contract that governs the request, passed as the **`contract`** argument.

**Locate the bundle first (bounded — do not improvise).** Before the first `generate_query`, resolve which bundle governs the data, in this order, then stop:

1. a bundle path the user named in chat, or one you already located this session (plus, **only** when **`features.contract_cache`** is **`true`**, a **`contract_hash`** returned earlier this session);
2. the **project convention** — a bundle directory **`./adi/contract/`**, or the path named in a **`.adi.yaml`** pointer at the working-dir root (`contract_path: <dir>`);
3. **none found → stop.** Do **not** scan the filesystem, re-call tools in a loop, or invent a location. Tell the user plainly: _"There's no ADI contract for this data yet — one has to be authored before I can answer questions on it,"_ then **offer to author one now** and, on yes, hand off to the **`adi-authoring`** skill. Authoring writes the bundle to `./adi/contract/`, so the original question can proceed straight after.

Once located, pass it as **`contract`**:

- **Every call** — send the bundle inline as `contract.documents`, a map of filename → file contents (strings). This is the default and, on the hosted service, the **only** working path: it keeps **no copy of your contract between requests** (**`features.contract_cache`** is **`false`**), so each request must carry the full bundle.

  ```json
  {
    "documents": {
      "contract.yaml": "<yaml text>",
      "entities.yaml": "<yaml text>",
      "metrics.yaml": "<yaml text>",
      "vocabulary.yaml": "<yaml text>",
      "policies.yaml": "<yaml text>"
    }
  }
  ```

  Include `policies.yaml` / `rules.yaml` only when the bundle has them.

  **Bundles are typically tens of KB — emitting the full YAML inline in the tool call is the expected, supported path.** Read each bundle file and pass its text **directly** as the `documents` value — you do **not** need shell tools (`jq`, `cat`) or temp files to assemble the payload. Send it on every call; only when `features.contract_cache` is `true` may later calls reuse a returned `contract_hash` instead (see below). Do **not** invent alternative delivery mechanisms: no direct HTTP calls that bypass the MCP session, and **never** read, extract, or handle host credential stores, keychains, session cookies, or OAuth tokens for any purpose — auth belongs to the MCP client, not to you. If the inline upload genuinely fails (e.g. size limit error from the server), report that error to the user; do not work around it.

  **Send each file exactly as it is on disk, and never trim it.** Read the files from disk before each call; the text you pass must be the file's full contents, character for character: do not shorten, reformat, summarise or retype any part of it, even a part you think is wrong. Do not change the contract files while querying: if the contract needs a change, say so and hand off to the `adi-authoring` skill. If the user changes the files during the session, the hash check below stops on the next call; once the user confirms the change, compare later hashes with the new one.

- **Reuse by hash — only when `features.contract_cache` is `true`.** Then, and only then, later calls may skip re-uploading with `contract={"contract_hash": "<hash from a prior response>"}`. **When it is `false` (the hosted default), never send a hash** — it can only refuse. A stale/unknown hash refuses with `contract_not_cached`; where caching is on but per-replica this can happen even for a hash you just received. Either way treat it as a **normal, expected outcome, not an error**: recover by re-sending the full `documents` and continue.
- Every successful `adi.generate_query` response carries a `contract_hash`, a fingerprint of the contract the SQL was compiled from. Treat it as an identity to compare: record the first one in the session, compare each later response's hash with it, and if one differs, stop and tell the user, because the contract sent has changed. Contract caching is off on the hosted server, so never send the hash in place of the contract.
- `documents` and `contract_hash` are **mutually exclusive** — sending both is `request_malformed`.
- **Do not "probe" without a contract at t1.** When `trust_tier` is `t1` (hosted), a `generate_query` call with no `contract` is **refused** — don't send a bare call to test reachability (that wastes a round trip). The first call must carry `documents` (a known `contract_hash` works only when **`features.contract_cache`** is **`true`** — never on the hosted default, where it is always refused). Only **local / T0 servers** with `ADI_CONTRACT_PATH` configured load a default contract from disk, so `contract` may be omitted there.

## Discovering valid identifiers

`adi.get_capabilities` returns server feature flags only — **not** the metric/dimension vocabulary. That vocabulary lives in the contract bundle you provide, so resolve user intent against the bundle itself:

- **Metric ids** — `metrics.yaml` → each `metric_id` (the only valid `metrics[]` values).
- **Dimensions / selectors** — a metric's `allowed_group_bys` lists the `entity.column` selectors permitted for it; `disallowed_group_bys` blocks specific ones.
- **Natural-language aliases** — `vocabulary.yaml` maps phrases to canonical ids (`vocabulary.metrics[].aliases → metric_id`, `vocabulary.dimensions[].aliases → selector`). Use it to translate e.g. "revenue" → the real metric id; never send an alias on the wire.

When a user's term maps to **more than one** contract metric (e.g. "revenue" → several revenue / GMV metrics that differ by gross-vs-net, settled-cash, or attribution), name the metric you're using **and** the one-line alternatives **before** you call `generate_query` — a hosted generation is slow, and the user should not first learn which "revenue" they got in the final answer. Proceed with the most defensible default unless they pick another. If one of those metrics carries the user's term as an alias in `vocabulary.yaml`, that metric is the default.

If you guess wrong, the refusal carries the valid options to recover from (e.g. `metric_not_found.details.available_metrics`, `dimension_not_allowed.details.allowed_group_bys`) — see [references/refusal_codes.md](references/refusal_codes.md).

## QueryRequest v1 shape

Use:

- `query_request_version: "1"` (required)
- `metrics: ["metric_id", ...]` (required, 1–8 unique ids)
- Optional:
  - `group_bys: ["entity.column", ...]` — selectors from the metric's `allowed_group_bys`.
  - `filters` — array of `{entity_ref, operator, value}` (see below).
  - `time_range` — `{type: "relative", value: "last_quarter", as_of: "YYYY-MM-DD"}` (relative tokens: `last_30_days`, `last_month`, `last_quarter`, `last_year`, `ytd`, `last_n_days` + `n_days`) or `{type: "absolute", start, end}`. Applies to each metric's canonical time column. For an absolute range, **`start` and `end` are both inclusive** of their calendar day — the window is `[start, end]`. To exclude the upper day (e.g. a clean month boundary like "all of June"), set `end` to the last day of the period (`2026-06-30`), or use a `filters` entry with `<` on the time column (`{entity_ref: "...", operator: "<", value: "2026-07-01"}`) instead.
  - `order_by: [{field, direction}]` — `field` must be one of your `metrics` or `group_bys`; `direction` is `asc`/`desc`.
  - `top_n` — integer 1–10000 (`LIMIT`; defaults ordering to `metrics[0]` desc when `order_by` is empty).

**Field names are exact, and the plural ones are plural.** The schema is closed, so any
unrecognised key is refused with `request_malformed` — including a near-miss like
`group_by`. Watch: `metrics` (not `metric`), `group_bys` (not `group_by`), `filters` (not
`filter`). Never send legacy keys either (`question`, `generate_sql` inputs). When you do
get it wrong, the refusal names the field you meant: `details.path` points at the key sent
and `suggestion` lists the permitted ones, closest first — read it rather than guessing.

### HTTP (direct JSON clients — for human integrators only)

If you are implementing a client outside MCP, use versioned routes only (unprefixed paths are not registered). When using this skill as an agent, do not make direct HTTP calls; use the MCP tools instead.

- `GET /v1/health`, `GET /v1/capabilities` — public
- `POST /v1/generate_query`, `POST /v1/validate`, `POST /v1/get_authoring_spec`, `POST /v1/execute_sql`, `POST /v1/replay_self_check` — auth + quota (same JSON bodies as the matching MCP tools)
- Optional top-level `row_limit` on `POST /v1/generate_query` caps result size (maps to `query_request.top_n` when unset)

### Filters

Each filter is `{entity_ref, operator, value}`. `entity_ref` is `entity_id.column` (or `entity_id[role].column`). Operator/value coupling:

| operator                                  | value                              |
| ----------------------------------------- | ---------------------------------- |
| `=` `!=` `<` `<=` `>` `>=` `like` `ilike` | single scalar                      |
| `in` `not_in`                             | array of scalars (1–1000, unique)  |
| `between`                                 | `[lo, hi]` (same type, `lo <= hi`) |
| `is_null` `is_not_null`                   | omit `value`                       |

Scalars are `string` / `int` / `float` / `bool`; dates are ISO strings (`"2026-01-22"`). Multiple filters are AND-ed. For date-range filtering on a non-canonical column, use `between` (or paired `>=` / `<`) rather than `time_range`.

## Coarser time grains (month / quarter / week)

`query_request` v1 has **no time-grain / bucketing** field. `group_bys` take raw `entity.column` selectors and `time_range` is a **filter window**, not a grouping — so grouping by a canonical _date_ column returns **daily** rows, not months. To answer "by month/quarter/week", roll up ADI's governed SQL **only when it is mathematically safe**:

- **Additive metrics only** — `expression.type: sum` or `count` in `metrics.yaml`. You may wrap the exact ADI-generated SQL in an outer `DATE_TRUNC('<grain>', …)` + `SUM(…)`, keeping the inner query **byte-for-byte unchanged**, and label it clearly as an **ungoverned wrapper** (ADI did not sign it).
- **Never for non-additive metrics** — `ratio` (e.g. average order value) and `count_distinct` (the non-additive `expression.type`s ADI can generate). An outer `SUM`/`AVG` over per-day values is **wrong** (a monthly average of daily averages is not the monthly average; summing daily distinct counts double-counts). Do **not** wrap these. Instead return the canonical (daily) grain, or **refuse the coarser grain and explain**, or — only if the user explicitly accepts leaving governance — compute it from raw.

Always check `metrics.yaml` `expression.type` before rolling up; when in doubt, return daily grain and say so.

## Reporting results faithfully

The contract's grain and additivity govern the write-up, not just the SQL. If a metric is kept in local currencies (no FX normalisation in the contract), report each currency separately and never sum them into one total. If a metric is `ratio` or `count_distinct`, never describe a total or an average of per-group values as the overall figure. When you are unsure whether two numbers can be combined, check the metric's `expression.type` and any `scope_note`, and if still unsure, present them separately and say so.

**Rankings on rate metrics need their denominators.** When a request orders or applies `top_n` on a `ratio` metric (a rate, share, or average), a group with a tiny denominator can top the ranking on noise alone — one conversion out of two visits outranks a thousand out of three thousand. When the contract exposes the denominator as a metric (or a supporting count), include it in the same request's `metrics` so every ranked row carries its sample size, and report it alongside the rate. Do not headline a leader whose denominator sits far below the rest of the field without flagging it; when the contract offers no denominator metric, say plainly that the ranking is not protected against small samples.

## Contract YAML validation (optional)

Use **`adi.validate`** on bundle YAML **only** when **`features.core_tools`** is **`true`** and **`enabled_tools`** lists **`adi.validate`** (same gate as **`generate_query`**). Prefer **`adi-authoring`** skill prose when authoring contracts from scratch; **`validate`** is for machine checks on an on-disk bundle.

When **`features.contract_cache`** is **`true`** (not the hosted default — there, `adi.validate` returns no hash and you send `documents` every time), a **clean** `adi.validate` (**`ok: true`**, no repairs) returns a **`contract_hash`** and primes the same per-tenant cache `generate_query` reads. So if you validate a bundle before querying it, reuse that `contract_hash` on the first `generate_query` instead of re-uploading `documents` (a miss still refuses with `contract_not_cached` — recover by re-sending `documents`, as under **Providing the contract**).

## Guardrails (non-negotiable)

- Use contract metric/dimension identifiers only; never invent fields.
- **Contract discovery is bounded.** Look only at {a hash cached this session, a path the user named, `./adi/contract/`, a `.adi.yaml` pointer}. If none is found, do **not** scan the filesystem, re-loop tools, or improvise a location — stop and offer to author a contract (see **Providing the contract**).
- Prefer refusal over guessing when contract mapping is ambiguous.
- Never write ad-hoc SQL manually when ADI tooling is available.
- **`adi.execute_sql`** is **only** for ADI-signed SQL from **`generate_query`**: all of **`query.sql`**, **`query.dialect`**, **`contract_hash`**, **`query.signature`** must come from the **same** successful response. Unsigned SQL **cannot** be executed through MCP — do not call **`adi.execute_sql`** without a valid **`signature`**.
- At **T1** (no signature), the generated SQL runs **client-side on the user's own warehouse** using a client the environment already has, or one the user agreed to install, or is handed to the user to run (see [Client-side execution (T1)](#client-side-execution-t1)). That does **not** relax the rule above. Never hand-run SQL by reading credentials, keychains, or tokens yourself, and never route unsigned SQL through **`adi.execute_sql`**.
- Respect policy-driven denials (PII/governance) and provide safe alternatives.
- **Report results faithfully to the contract's grain and additivity.** In the written answer, do not blend values the contract keeps separate (for example local currencies it does not normalise) and do not present a non-additive metric (`ratio`, `count_distinct`) as a single summed figure. Report split figures split, and state the grain. The compiled SQL is correct; the narration is where this breaks, especially on a cheaper query model.
- **Never headline a rate ranking without its denominators.** When ranking (`order_by` / `top_n`) on a `ratio` metric, request the supporting count in the same call when the contract exposes one, report it with each rate, and flag — or decline to headline — entries whose sample size is too small to support their rank (see **Reporting results faithfully**).
- **Never touch auth material.** Do not read/extract keychains, credential stores, session tokens, or OAuth secrets, and do not make direct HTTP calls that bypass the authenticated MCP session. The MCP client owns auth; large inline `contract.documents` uploads are the supported path (see **Providing the contract**).
- When the contract includes `rules.yaml` guardrails with `high_cardinality_group_by_mode: refuse`, grouping by primary keys or other high-cardinality columns without `top_n` may refuse with `high_cardinality_refused` — add `top_n`, pick a lower-cardinality dimension, or use `refusal.details.safe_alternatives`.

## Refusal playbooks

On refusal, consult [references/refusal_codes.md](references/refusal_codes.md) for the full refusal-code table, clarification handling, and connection-failure recovery.

## Trust posture

- Contract-driven requests only.
- Refusal over guessing.
- No bypasses (no unsigned SQL through **`adi.execute_sql`**, no policy evasion).
- Explain provenance and warnings in user-facing answers.

## Examples

See [examples/sample_queries.md](examples/sample_queries.md) for pattern-based examples.
