---
name: adi-authoring
description: >-
  Produces a valid ADI Contract v1 YAML bundle (contract, entities, metrics,
  vocabulary, optional policies/rules) from live database metadata. Use when the
  user asks for an ADI contract, ADI Contract v1, semantic contract bundle,
  contract.yaml for analytics, or governance YAML aligned to a warehouse schema.
  Assumes the agent can query INFORMATION_SCHEMA or equivalent to list catalogs,
  schemas, tables, columns, keys, and comments. When MCP exposes authoring tools,
  prefer them after adi.get_capabilities confirms features.authoring_tools.
  When execute_sql is enabled on the server, use adi.replay_self_check to replay
  contract self_check assertions against the attached warehouse.
license: Apache-2.0
compatibility:
  - Claude Code
  - Claude Cowork
  - Cursor
  - OpenClaw
  - Manus
  - Codex
metadata:
  author: agentic-data-intelligence
  version: "1.7.0"
mcp_tools:
  - adi.get_capabilities
  - adi.get_authoring_spec
  - adi.validate
  - adi.generate_query
  - adi.replay_self_check (not available on the hosted tier, t1)
  - adi.session.configure_scope (not available on the hosted tier, t1)
  - adi.schema.list_objects (not available on the hosted tier, t1)
  - adi.schema.get_table (not available on the hosted tier, t1)
  - adi.schema.get_tables_batch (not available on the hosted tier, t1)
  - adi.profile.table (not available on the hosted tier, t1)
  - adi.profile.column (not available on the hosted tier, t1)
  - adi.schema.create_snapshot (not available on the hosted tier, t1)
---

# ADI Contract v1 bundle (agent authoring)

## MCP authoring helpers (when capabilities allow)

Call **`adi.get_capabilities`** first. **Authorization check (before anything else):** if the response has an **`authorization`** block and **`authorization.status`** is **`"pending_approval"`** (or, on older servers without `status`, **`authorization.authoring_role_granted`** is **`false`**), you are authenticated but **not approved**. Lead with that fact — relay **`authorization.message`** verbatim when present (it names the exact role and the correct retry guidance); otherwise tell the user their access is pending approval (an admin must grant the role). Then **stop** — do not introspect, profile, or author, and do **not** present role flags or `enabled_tools` as capabilities the user "has" while approval is pending. You may **offer to re-check periodically** (re-call `adi.get_capabilities` on the user's say-so) and continue automatically once `status` flips to `approved` — no re-login needed — so the user isn't left manually polling. (No `authorization` block means auth isn't role-gated here — proceed.)

If `adi.validate` or `adi.generate_query` returns an error with the code `insufficient_role`, the account's ADI access is still pending approval. Tell the user so, as the error message says. Then stop. It is an error, not a refusal, so it is not in the refusal codes.

Use MCP authoring/schema/profile tools **only** when **`features.authoring_tools`** is **`true`** and **`enabled_tools`** lists them — for example **`adi.session.configure_scope`**, **`adi.schema.list_objects`**, **`adi.schema.get_table`**, **`adi.schema.get_tables_batch`**, **`adi.profile.table`**, **`adi.profile.column`**, **`adi.schema.create_snapshot`**.

> **Hosted ADI endpoint (the public plugin) is T1 → `features.authoring_tools` is always `false`.** The server gates authoring tools on a T0 trust tier **with** a configured database; the hosted Starter endpoint is T1, so `get_capabilities` will **not** report them there. Do not wait for or expect them against the hosted server — go straight to the **client-side warehouse metadata** path below (`INFORMATION_SCHEMA` / `SHOW …` run with the access the environment already has). The authoring-tool path applies only to a **self-hosted T0** server with a database URL set.

- **`adi.get_authoring_spec`** — **the canonical JSON Schema plus semantics** (the enums, `type_mapping`, `engine_dialect_map`, and cross-document validation rules) for your **`spec_version`**. **Call it early — immediately after `adi.get_capabilities` confirms it is in `enabled_tools`** — and author against it. Where this skill's prose and the spec disagree, **the spec wins** — the enums and maps quoted below are a convenience copy that can lag the server.
- **`adi.validate`** — validate a contract bundle when **`features.core_tools`** is true and **`enabled_tools`** includes **`adi.validate`**. This is the authoritative validator (structure, cross-document semantics, a compile dry-run over every metric and its allowed_group_bys, and — with schema metadata — warehouse alignment).
- **`adi.replay_self_check`** — when **`features.execute_sql`** is **`true`** and **`enabled_tools`** includes **`adi.replay_self_check`**, replay **`contract.self_check.assertions`** SQL against the MCP warehouse (requires server **`ADI_MCP_EXECUTE_SQL`** / configured executor — same gate as **`adi.execute_sql`**). Pass the bundle per **Bundle payload shape** below — or, to avoid re-uploading, reference a bundle you already validated by **`contract_hash`** (see **Reuse a validated bundle by hash**). Optional **`assertion_names`** to filter. Use after structural validation when **`self_check`** is present.

### Bundle payload shape (`adi.validate` and `adi.replay_self_check`)

Both tools take a single **`bundle`** argument that must set **exactly one** of these keys (setting neither or both is rejected with `invalid_bundle_input` — _"Exactly one of bundle_dir or documents must be set"_):

- **`bundle.documents`** — a map of bundle filename → **raw YAML string**. The server parses each string itself, so do **not** pass pre-parsed objects (filename-keyed dicts are rejected). Required documents: **`contract.yaml`**, **`entities.yaml`**, **`metrics.yaml`**, **`vocabulary.yaml`**; optional: **`policies.yaml`**, **`rules.yaml`**.
- **`bundle.bundle_dir`** — an absolute path the **server** reads the bundle from. Usable **only** when the server shares your filesystem (self-hosted / local). The **hosted server cannot read your files**, so `bundle_dir` will fail there.

**Use `documents` for the ADI plugin — do not try `bundle_dir` first.** The plugin runs locally but connects to a **remote** server, so the server can't see your disk; `bundle_dir` is for a self-hosted server only. Read each bundle file you authored and pass its **text directly** as the string value (key = filename) under `documents`. Bundles are tens of KB and inline is the **expected, supported path**: you do **not** need to escape newlines, build the payload with a script, or use `jq` / `cat` / temp files — pass the raw file contents as the string and the MCP client serializes it (multi-line YAML included).

```jsonc
// adi.validate — inline documents form
{
  "bundle": {
    "documents": {
      "contract.yaml": "<raw yaml text>",
      "entities.yaml": "<raw yaml text>",
      "metrics.yaml": "<raw yaml text>",
      "vocabulary.yaml": "<raw yaml text>",
    },
  },
  "checks": ["structure", "semantic"], // optional; default runs all four (adds "compile" and "warehouse")
}
```

`adi.validate` also accepts `schema_snapshot_id` / `schema_metadata` (warehouse checks), `strict`, and `apply_repairs` (returns `repaired_documents`). **Determinism backstop:** when you have client-side warehouse metadata, pass it as inline `schema_metadata` together with `apply_repairs` and adopt the returned `repaired_documents` — the server then re-canonicalizes column spelling, numeric types, `time.canonical`, currency refs, and PII policies deterministically; then re-validate clean (no `apply_repairs`) to confirm the repaired bundle — which also returns its hash when `features.contract_cache` is `true`, per below. `adi.replay_self_check` takes the same `bundle` plus optional `assertion_names`.

Pass inline `schema_metadata` in this format. In our tests, a shorter format the server did not read failed as `physical_table_missing` ("does not match any inspected table") rather than saying the metadata was not understood. Keep every key shown: the shorter form had only `catalog`, `schema` and `name` for the table and `name` and `type` for each column.

```json
{
  "tables": [
    {
      "fqn": "analytics.main.orders",
      "table_catalog": "analytics",
      "table_schema": "main",
      "table_name": "orders",
      "columns": [
        {
          "name": "order_id",
          "column_name": "order_id",
          "data_type": "INTEGER"
        },
        { "name": "country", "column_name": "country", "data_type": "VARCHAR" }
      ]
    }
  ]
}
```

### Reuse a validated bundle by hash — only when `features.contract_cache` is `true`

The contract bundle is typically tens of KB; re-sending `documents` on every `adi.validate` and `adi.replay_self_check` call is the dominant cost of the authoring loop. When **`features.contract_cache`** is **`true`** (from `adi.get_capabilities`), upload the bundle **once** and then reference it by hash — the same per-tenant cache **`adi.generate_query`** uses:

1. Call **`adi.validate`** with `bundle.documents`. On a **clean** result (**`ok: true`** with **no repairs**), the response carries a **`contract_hash`**.
2. Call **`adi.replay_self_check`** (or, in the **`adi-querying`** skill, **`adi.generate_query`**) with **`{"contract_hash": "<hash>"}`** instead of re-sending `documents`.

Rules and recovery:

- A miss returns **`contract_not_cached`** (carrying the `contract_hash`). This is **normal, not an error** — on hosted multi-replica servers the cache is per-replica, so a hash you just received can still miss. Recover by re-sending the full `documents` (which re-caches) and continue; do not treat it as a failure or invent a workaround.
- **Repairs break the hash.** When you call `adi.validate` with `apply_repairs` and it returns `repaired_documents`, **no `contract_hash` is returned** — the repaired bundle is a different artifact. Write the repaired documents to disk, then `adi.validate` them again **clean** (no `apply_repairs`) to obtain the hash for the final bundle.
- **`contract_hash` is an input only to `adi.replay_self_check` and `adi.generate_query`, never to `adi.validate`.** `adi.validate` _emits_ the hash but cannot consume one — always send it `documents` (or `bundle_dir`). So: set exactly one of `documents` / `bundle_dir` on `adi.validate`; set exactly one of `documents` / `bundle_dir` / `contract_hash` on `adi.replay_self_check`; and set exactly one of `documents` / `contract_hash` on `adi.generate_query` (it takes **no** `bundle_dir`).
- **`contract_cache_ttl_seconds`** (from capabilities) is how long a hash stays referenceable; re-upload once it expires. It is `null` when caching is off.

When **`features.contract_cache`** is absent or **`false`** — **the hosted default**, where the service keeps no copy of your contract between requests — skip this entirely and pass `documents` every call. That is the expected, supported path; a hash there can only refuse.

If authoring tools are **absent** or **`features.authoring_tools`** is **false** (the Starter/**T1** posture — there is **no warehouse MCP tool**), run introspection and profiling SQL **client-side against the user's own warehouse using whatever access the environment already provides** — native introspection (`INFORMATION_SCHEMA`, `SHOW CREATE TABLE`, catalog commands), the user's own SQL client, a notebook/JDBC connection, or metadata exports. ADI does not ship or manage a client-side runner. **Never read, inspect, or ask the user for credential files, keychains, or tokens yourself** — any SQL client must be run by the user (or through a connection they have already configured). If you cannot run SQL in this environment, ask the user to run the introspection queries and paste the results. Follow **Workflow** with whatever access you have; this skill's YAML rules do not change.

## Goal

Emit a **directory of YAML files** that together form one **ADI Contract v1.0 bundle**: a machine-validable analytic contract over **physical** tables the agent has inspected. Do **not** invent tables, columns, or joins that the database does not support.

## Agent bundle (ship these together)

Organizations should give the agent a **single distributable set** of artifacts in one workspace or folder:

| Artifact                                        | Role                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **This skill** (`SKILL.md`)                     | Authoring rules, workflow, checklist, validation strategy.                                                                                                                                                                                                                                                        |
| **JSON Schema** (`schemas/*.schema.json`)       | Formal document/bundle shape for offline structural validation, bundled with this skill under `schemas/` — self-contained static files, no dependency to install. `adi.validate` (MCP) remains the authoritative check.                                                                                           |
| **Dataset / domain context** (one or more docs) | Business meaning, metric intent, grain definitions, known PII or sensitivity, currency/FX expectations, subject-area glossary, lineage notes—anything that improves **titles**, **descriptions**, **vocabulary aliases**, **policies**, **scope_note**, and **join semantics** without replacing warehouse truth. |

**Grounding rule:** context documents **inform** wording and governance; **introspection** (or authoritative metadata exports) remains the source of **what tables and columns exist**. If context conflicts with DDL, **fix the contract to match physical reality** and flag the doc drift to the user.

## Outputs (files)

Write the bundle to the **project convention `./adi/contract/`** (UTF-8; the ADI server parses YAML 1.2, so bareword `on`/`off`/`yes`/`no` are read as strings) unless the user names another location — in which case also record it in a `.adi.yaml` pointer at the working-dir root (`contract_path: <dir>`). This is the location the **`adi-querying`** skill discovers automatically, so a freshly authored contract is queryable with no further setup.

| File              | Required                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------ |
| `contract.yaml`   | **Yes**                                                                                    |
| `entities.yaml`   | **Yes**                                                                                    |
| `metrics.yaml`    | **Yes**                                                                                    |
| `vocabulary.yaml` | **Yes**                                                                                    |
| `policies.yaml`   | Optional (use when PII/sensitive columns exist)                                            |
| `rules.yaml`      | Optional (FX rules, advanced governance; only if you reference them from metrics/contract) |

Write the decisions record from Workflow step 3 to `./adi/DECISIONS.md`, beside the bundle directory (when the user names another bundle location, to `DECISIONS.md` in that location's parent directory). It is not a bundle document, so never send it to ADI.

## Workflow (when database access exists)

1. **Gather domain context — ask the user explicitly.** Before introspecting, request the documents that define **meaning** (introspection covers structure; nothing else covers meaning). At minimum ask for:
   - a **metrics / KPI glossary** — how each business metric is defined (what counts as “revenue”, “active”, “churned”, “acquired”);
   - a **revenue-recognition policy** — which order states count as realised revenue, and the treatment of cancellations, refunds, unpaid/pending orders, gift cards, tax, and shipping;
   - a **data dictionary** — column meanings, status/enum code lists, and which timestamp is the business event;
   - a **PII / sensitivity classification** — which columns are sensitive and how they must be handled.
   - **a few figures the user already trusts**, each with its period and where it came from (for example one day's order count, or last month's revenue), so the finished contract can be checked against them.

   These populate the **Dataset / domain context** artifact in the Agent bundle above. Accept any subset the user has; record which are missing.

   > **If the user supplies none of these, say so loudly and specifically before authoring — do not silently proceed on the schema alone.** Without a glossary and a revenue-recognition policy, every business definition below becomes a **guess inferred from column names**: “revenue” may silently include cancelled, unpaid, or gift-card orders; “acquisition”/“active” may be measured by the wrong timestamp (e.g. registration date instead of first activity), masking real trends the data would otherwise show. The resulting numbers can be internally consistent and **defensible, but they are not authoritative** — and each debatable call propagates into every metric, policy, vocabulary alias, and `scope_note` built on top. Without a PII/sensitivity classification, `policies.yaml` is inferred from name patterns alone and **will miss non-obvious sensitive columns**. Obtain the documents, or an explicit user acknowledgement of these costs, before continuing.

2. **Resolve scope** from the user: catalog/database name, schema name, and optional table allowlist/denylist.
3. **Resolve the contestable definitions explicitly, and record each decision.** Before authoring metrics, write down the chosen answer to every definition the data leaves open, so a second author (or the same author on another day) would reproduce it. At minimum decide and record: entity succession (does a renamed or split entity roll up to a predecessor); event-versus-transaction grain (does one row equal one business event); additivity (which metrics may be summed across time or dimensions); in-progress and as-of handling (is the latest period complete, and what "as of" date governs "latest"); and scope (which population the metric covers). **A definition the user supplied binds.** Where a context document defines a term, author that term's metric to that definition, under the user's name for it. Give that metric the user's term as an alias in `vocabulary.yaml`. If a supplied definition can be read more than one way on this data (for example, whether a cancellation invoice counts as an order), author it on its plain, literal reading and list it under "Departures from your documents", marked CONFIRM, with the reading the contract took, so the user decides. The same applies where a supplied definition is silent on a case the data contains (for example, whether gift cards count in a defined revenue): that is a question for the user, not an assumption. If you think the definition is wrong, ambiguous or a poor fit for the data, do not substitute your own reading: keep the user's metric as defined and propose your alternative to the user as a separate, named metric (for example `sale_order_count` beside `order_count`), with the reason. Add it to the contract only if the user agrees, and never give it the user's term as an alias. Where the data cannot support a supplied definition as written, that is a departure from the user's documents: record it as described below and ask. Revisit these points after introspection and profiling (steps 4 and 5), when you can see what the data contains. Where no context document covers a point and no supplied definition bears on it, either ask the user or record it as an assumption with its cost. For each metric, set `allowed_group_bys` to the modelled dimensions that are valid for it, so grouping is locked to a known-correct grain; only leave it open as a recorded, deliberate decision, and never expose a group-by that has no supporting key. Then test the whitelist against demand, not only correctness: list the questions users of this domain predictably ask — leaderboards and per-entity rankings, breakdowns by the obvious categorical columns, trends over time — and for each one either confirm some metric's `allowed_group_bys` answers it or record an explicit decision to exclude it, with the reason. The whitelist exists to block incorrect grains, not unanticipated questions: a breakdown the data supports but the list silently omits is not governance, it is a wrong refusal waiting to happen.

   **Departures from the user's documents come first in the decisions record.** Open the decisions record (`./adi/DECISIONS.md`, see **Outputs**) with a section headed "Departures from your documents". List there, before any other decision, every point where the contract departs from a document the user supplied, and every open question about one, each marked CONFIRM, with the document's wording, what the contract does (for a departure, what it does instead), and why. If no document was departed from and no question is open, say so in that section. Authoring is not finished while any item in that section is unconfirmed: list them for the user in one message and ask.

4. **Introspect** using the warehouse’s metadata APIs (e.g. `INFORMATION_SCHEMA`, `SHOW CREATE TABLE`, or native catalog commands). When MCP authoring tools are available (see above), prefer **`adi.session.configure_scope`** then **`adi.schema.*`** / **`adi.profile.*`** instead of ad-hoc SQL where they cover your needs. **When those tools are absent (the Starter/T1 posture), run the metadata queries client-side against the user's own warehouse using the access the environment already provides** — e.g. `SHOW TABLES`, `DESCRIBE <table>`, or `INFORMATION_SCHEMA` selects — rather than assuming a warehouse MCP tool exists. Collect for each in-scope table:
   - Fully qualified physical name (how SQL references it).
   - Table type (table/view).
   - Column names, declared types, nullability.
   - Primary key / unique constraints if available.
   - Foreign keys if available.
   - Table/column comments if available.
5. **Infer semantics conservatively** from names + types + profiling if the agent can run safe `SELECT` aggregates (distinct counts, min/max for numerics, small samples for strings) — at T1, run those profiling selects client-side with the warehouse access you already have. Do not guess FX or currency semantics without evidence (currency-like column names, amount columns, rate columns).
   - **Use the spec's deterministic markers as the first pass for column classification.** Match each column name (case-insensitive) against `semantics.column_hints_and_inference.roles` from `adi.get_authoring_spec`, honouring the two match modes: `*_tokens` entries match only by **exact equality** with the whole name or one of its `_`/`-`-separated parts, while `*_substrings` entries match **anywhere** in the name — never substring-scan a token list (CDC token `op` matches `op_code` but not `shop_id`). Where a name matches, take the mapped role — `amount` → a `sum` measure; `currency` / `fx_normalization` → currency handling; `system_time` → never `time.canonical`; `cdc_marker` → `row_scope`; `pii_sensitive` → a `policies.yaml` mask/pii row; `geo_quasi_identifier` trigger → require companion-column coverage. This converges the common cases so two authors agree on them. **The lists are deliberately narrow and never complete** — still classify by meaning (names + types + domain context) for columns they don't catch, and never read "not in the list" as "not sensitive / not an amount". The markers reduce variance; they don't replace judgment.
   - **Reason about what the data does not contain.** State plainly what the tables have no record of (a superseded entity, a category the schema cannot express, a period the source stopped covering) and whether the most recent period is complete. Encode the finding: refuse the affected question through the contract, or carry an honest `scope_note`, rather than inferring a value the data does not support or repeating a silence in the source documentation.
   - **Every `count_distinct` identity column is a deliberate, data-verified choice.** A fact routinely carries several plausible columns for the same conceptual "who" — the actor and the party who acted on their behalf, the business entity and a technical/surrogate key — that all compile cleanly yet disagree by orders of magnitude. Before declaring any `count_distinct` metric, profile the distinct count of **every** candidate identity column and choose by which population's size and shape matches the business entity being counted; the column name and dictionary phrasing are **not** evidence — sources routinely label the on-behalf-of party as the "payer"/"sender", and a "customers" count in the tens against a sibling column in the tens of thousands is a red flag, not a coin flip. When plausible candidates disagree materially, treat the choice as a contestable definition: record it (step 3), state the chosen column, the rejected candidate, and **both** distinct counts in the metric's `scope_note`, and pin the choice with a `self_check` assertion (see **`contract.yaml` → `self_check`**). When the name points one way and the data shape the other, ask the user; if the user is unreachable, surface the conflict loudly rather than silently picking.
6. **Author `contract.yaml`** with correct `datasource` and `defaults` (see below).
7. **Author `entities.yaml`**: one entity per physical table you include; `physical` must match introspection; `columns` must list analytic-relevant columns; PK/grain/time must be consistent with metadata.
8. **Author `metrics.yaml`**: metrics only over declared entities; expressions reference `entity_id.column` consistently. **Enumerate the metric set from an explicit source, not from what looks interesting:** author exactly one metric per glossary/KPI term gathered in step 1 (plus any alternative the user agreed to in step 3); when no glossary was supplied, author one metric per identified measure column (the step-5 `amount` markers are a starting point, not the full set — include any additive measure you find) and record the un-glossaried coverage as an assumption (step 3). This makes the _set_ of metrics reproducible across runs, not just each metric's shape.
9. **Author `vocabulary.yaml`**: aliases for metrics and dimensions you defined.
10. **Author `policies.yaml`** when any column is PII/sensitive (email, phone, address, IP, device ids, free-text PII, precise geo) or when introspection marks columns as sensitive.
11. **Self-check** using the validation checklist below (parse YAML, cross-reference IDs), then run **`adi.validate`** until clean (see **Machine validation**).
12. **Check the contract against the figures the user trusts.** After `adi.validate` is clean, for each figure from step 1, generate the governed query with `adi.generate_query` and run it as the `adi-querying` skill describes (or ask the user to run it). If any result differs from the user's figure, stop: show the user both figures and the metric's definition, and do not treat the contract as finished until the user has decided. Record the user's decision in the decisions record. If the user has no trusted figures, say that this check was not run, and record that in the decisions record. Run this step again after any change to the bundle.

## `contract.yaml` (required shape)

Top-level keys (exact intent):

- `adi_contract_version`: string **`"1.0"`**
- `contract_id`: stable snake_case identifier
- `title`: human-readable string (not top-level `name` or `version`)
- `datasource`: object with **only** these keys:
  - `engine`: one of `databricks` | `snowflake` | `spark` | `bigquery` | `postgres` | `duckdb` | `other` (use what matches the warehouse)
  - `default_catalog`: catalog/database name for defaults
  - `default_schema`: schema name for defaults
  - `sql_dialect`: one of **`spark` | `snowflake` | `bigquery` | `postgres` | `ansi` | `other`**. There is **no `databricks` and no `duckdb` dialect literal** — those are `engine` values only. Map `engine` → `sql_dialect`:

    | `engine`     | required `sql_dialect`                                                                     |
    | ------------ | ------------------------------------------------------------------------------------------ |
    | `databricks` | `spark` (never `databricks`)                                                               |
    | `spark`      | `spark`                                                                                    |
    | `snowflake`  | `snowflake`                                                                                |
    | `bigquery`   | `bigquery`                                                                                 |
    | `postgres`   | `postgres`                                                                                 |
    | `duckdb`     | **`postgres`** — DuckDB shares the postgres dialect; `sql_dialect: duckdb` is **rejected** |
    | `other`      | `ansi` or `other`                                                                          |

    This table is the offline copy; when MCP is available, the server's `engine_dialect_map` (from `adi.get_authoring_spec`) is the canonical source and returns only contract-valid literals.

- `defaults`: **exactly** three keys:
  - `timezone`: IANA name or clear label
  - `currency`: ISO 4217 (e.g. `USD`)
  - `row_limit`: integer between 1 and 100000

Do not add extra keys under `defaults` (no `fiscal_calendar`). Do not duplicate catalog/schema under other property names inside `datasource`.

## `entities.yaml`

- Top-level key: `entities`: **array** of entity objects.
- Each entity:
  - `id`: lower_snake_case, unique
  - `kind`: `fact` | `dimension` | `bridge`
  - `physical`: fully qualified name as in the warehouse (consistent with introspection)
  - `primary_key`: array of **physical** column names
  - `grain`: **array** of physical column names (never a prose sentence)
  - `columns`: array of `{name, type}` where `type` uses contract enums: `string` | `boolean` | `integer` | `number` | `decimal` | `date` | `timestamp` | `json`. The seeder narrows numeric types to the canonical form derived from warehouse metadata: `INTEGER`/`INT`/`BIGINT`/`SMALLINT`/`TINYINT`/`LONG` → `integer`; `DECIMAL`/`NUMERIC`/`NUMBER` (parametrized or not) → `decimal`; `FLOAT`/`DOUBLE`/`REAL` → `number`. Authoring agents should use the same vocabulary for consistency; the contract enum has no separate `double` literal.
  - **Facts** should include `time.canonical` pointing to the **business/event** timestamp column when one exists; avoid `created_at` / `updated_at` / ingest-only columns as canonical when a business time column exists. On an entity, `time.canonical` is a **bare column name** scoped to that entity (e.g. `order_placed_at`), **not** a qualified ref — contrast the metric-side rule under `metrics.yaml`.
  - **Joins** (optional): each join has `to` (target entity id), `on` as array of `{from, to}` pairs (use keys **`from` and `to`** for column mapping), and a **required `cardinality`** — one of `1:1` | `1:n` | `n:1` | `n:m` (no default; a join that omits it fails validation). If multiple joins target the same `to` entity, each join must have a distinct `join_role` (snake_case). Example (the ADI server parses **YAML 1.2**, so the `on:` key is safe unquoted; quote it as `"on":` only if you also hand-edit the bundle with older YAML-1.1 tooling):

    ```yaml
    joins:
      - to: customers
        on:
          - { from: customer_id, to: id }
        cardinality: n:1
    ```

  - **CDC / soft-delete / ingest markers**: set `row_scope` on the entity when applicable: `raw_all_rows` | `current_non_deleted` | `latest_by_pk` | `event_log`. **`current_non_deleted` requires an `is_deleted` column** on the entity (in `columns`); without it, `adi.validate` rejects the contract (semantic check) and `generate_query` refuses with `contract_invalid` — do not use this scope on tables that lack a soft-delete marker. For `latest_by_pk`, document tie-break preference (e.g. `updated_at`, then ingest time, then `created_at`) in the **domain-context docs** if unclear from DDL — **not** on the entity (see strictness note below).

**Entities are strict** (`additionalProperties: false`). An entity object accepts **only** these keys: `id`, `kind`, `physical`, `primary_key`, `grain`, `unique_keys`, `time`, `row_scope`, `columns`, `joins`. There is **no entity-level `description`** field — adding one (or any other extra key) **fails validation**. Put narrative, grain rationale, and tie-break notes in the domain-context docs, not in the YAML.

Prefer **n:1** joins toward dimension **primary** (or documented unique) keys when metadata supports it.

## `metrics.yaml`

- Top-level key: `metrics`: array.
- Each metric: `metric_id`, `title`, `base_entity`, `expression`.
- **Do not copy the `metrics_example` snippet from `adi.get_authoring_spec`.** It uses an `expr:` key, which the spec's own JSON Schema rejects (a metric takes no extra keys). Follow the schema, which wins, and the example in this skill: `metric_id`, `title`, `base_entity`, and `expression` with a `type`, as in the ratio example below.
- `expression.type`: `sum` | `count` | `count_distinct` | `ratio`
  - **Choose the type from the measure column's meaning, using the step-5 markers as a consistent first pass:** a unique id / primary-key column → `count_distinct`; an additive money/quantity measure → `sum` (the step-5 `amount` markers catch the common names — `*_amount`, `total_*`, `revenue`, `price`, `fee` — but any additive measure qualifies, matched or not); plain row frequency with no measure column → `count`; an explicitly-declared rate/share (numerator ÷ denominator) → `ratio`. Applying the same rule makes the same concept get the same `expression.type` + column across runs.
  - `sum` and `count_distinct` require `expression.value` as **`entity_id.ColumnName`** (entity id lower_snake, column as declared on entity). For `count_distinct`, the `value` column must be the **data-verified identity choice from Workflow step 5** — never the name-obvious candidate taken on faith.
  - **`ratio`** — for a derived rate such as average order value. Set `numerator` and `denominator`, each an operand `{type, value}` whose `value` is an `entity_id.ColumnName`. The operand types are **fixed, not interchangeable**: **`numerator.type` must be exactly `sum`** and **`denominator.type` must be exactly `count_distinct`** — no other value (including plain `count`) and no other combination is legal. The server compiles ratio metrics to correct signed SQL (numerator ÷ denominator):

    ```yaml
    metrics:
      - metric_id: average_order_value_eur
        title: Average order value
        base_entity: orders
        expression:
          type: ratio
          numerator: { type: sum, value: orders.amount }
          denominator: { type: count_distinct, value: orders.order_id }
    ```

  - **Not expressible as a contract metric** (no `expression.type` covers them): medians and other percentiles, duration/latency aggregates, custom or compound rates beyond a single numerator ÷ denominator, and concentration indices (e.g. Gini, HHI). Compute these **downstream** from contract metrics or raw SQL — do **not** approximate them with `sum` / `ratio`.

- **`time.canonical` (optional, metric-level)**: when set, it must be a **qualified `entity.column`** reachable from `base_entity` (e.g. `orders.order_placed_at`), **never** a bare column name. This is the **opposite** of the entity-level `time.canonical` (a bare column scoped to its entity). A structural check does not catch the bare-column form here — only **`adi.validate`**'s cross-document semantic layer does — so it can ship silently if you skip semantic validation. Mixing the two conventions is a common cause of validation failures.

### Monetary metrics (strict)

- Use **evidence** from the schema: amount columns, currency columns, FX/rate columns, or explicit rules—do not assume USD for mixed-currency facts.
- **Multi-currency facts**:
  - If a **validated FX path** exists (rate column on the fact, `rules.yaml` `fx_rules`, or explicit `normalization_ref` / `fx_rule` references that you actually define): prefer **normalized** semantics: `amount_semantics: normalized`, `unit.kind: currency`, `unit.code: USD`, `currency_column_ref`, `normalization_ref` and/or `unit.fx_rule` as appropriate.
  - If **no** FX path exists: use `amount_semantics: local`, `currency_column_ref`, honest `unit.code` (e.g. ISO `XXX` when mixed), `allowed_group_bys` on currency and/or `scope_note` restricting analysis—do **not** claim USD normalization.
- **Never** set `unit.code: USD` for normalized semantics **only** because `defaults.currency` is USD.
- `normalization_ref` uses `;key=value` modifiers after the core ref. **`cast=double`** (e.g. on `fx_column:entity.col;cast=double`) tells downstream SQL generators to widen amount × rate before multiply. **`fx_table:physical`** requires **`as_of=entity.column`** (valuation date on the join path from `base_entity`); optional **`quote=USD`** (default quote if omitted), **`base=…`**, and column renames **`rate_date_col`**, **`base_currency_col`**, **`quote_currency_col`**, **`rate_col`** when the FX table does not use the standard names. The server's **`adi.get_authoring_spec`** is the canonical source for these modifiers; **`adi.validate`** enforces them.
- **`EntityColumn.ref`**: a column on entity A may point at `B.col` when A joins to B — logical projection (e.g. currency from a parent fact). Runtime SQL must join and project; the physical table for A may not have that column.

If the metric **title** implies a filter (e.g. “active”, “open”) that the expression does not enforce, add `scope_note` or fix the title.

## `policies.yaml` (when needed)

Shape:

```yaml
policies:
  columns:
    - selector: entity_id.column_name
      action: deny | mask | redact
      classification: pii # optional; if present, one of: pii | sensitive | confidential | public
```

`selector` and `action` are **required**; `action` must be **`deny` | `mask` | `redact`**. `classification` is **optional** (omit it or set it null) — but **when present** it must be one of the closed enum **`pii` | `sensitive` | `confidential` | `public`**; do **not** invent values like `pii_direct_identifier` (rejected by validation). Do **not** emit a bare array under `policies`. Do **not** use `column_policies` or `policy_id` instead of `policies.columns` + `selector`.

Cover **all** sensitive columns (metadata hints + obvious name patterns), not only the most visible fields.

## `vocabulary.yaml`

Top-level:

```yaml
vocabulary:
  metrics:
    - metric_id: ...
      aliases: [...]
  dimensions:
    - selector: entity_id.column_name
      aliases: [...]
```

Both **`vocabulary.metrics`** and **`vocabulary.dimensions`** are **required keys** — include both even when one is empty (use `[]`); omitting either fails validation. Aliases: 1–128 characters. Align wording with **local vs USD-normalized** monetary semantics (do not imply global USD additivity for local-currency metrics).

## `rules.yaml` (optional)

Only add if metrics reference `fx_rules` or contract references rules. If omitted, do not leave dangling `unit.fx_rule` or orphan `contract.ruleset` references.

An `fx_rules` entry has this **exact** shape (the object forbids extra keys — do **not** improvise fields like `stored_direction` or `apply`):

```yaml
adi_contract_version: "1.0"
fx_rules:
  - id: usd_from_local # referenced by a metric via `normalization_ref: fx_rule:usd_from_local`
    rate_entity: fx_rates_daily # an entity id defined in entities.yaml
    rate_date:
      ref: payments.payment_date # qualified entity.column (valuation date, reachable from the metric base_entity)
      cast: date # const — must be the literal "date"
    base_currency_ref: payments.currency # qualified entity.column holding the source currency
    quote_currency: USD # target currency code (plain string, not a ref)
    rate_column: fx_rate # bare column name that exists on rate_entity
    on_missing: refuse # one of: refuse | null | warn_null
```

Required keys per rule: `id`, `rate_entity`, `rate_date.{ref,cast}`, `base_currency_ref`, `quote_currency`, `rate_column`, `on_missing`. `rate_entity` must be a defined entity and `rate_column` must exist on it; `rate_date.ref` and `base_currency_ref` are **qualified `entity.column`** refs. A metric opts into a rule with **`normalization_ref: fx_rule:<id>`**, where `<id>` must match a rule here (otherwise validation fails). `rules.yaml` may also carry `missing_data_rules` and `guardrails` arrays.

## `contract.yaml` → `self_check` (optional)

The contract spec allows a `self_check.assertions` array on `contract.yaml` so downstream validators (or the runtime) can replay authoring-time invariants instead of re-deriving them. Every assertion is dialect-agnostic SQL paired with a qualitative expected outcome:

```yaml
self_check:
  assertions:
    - name: pk_unique__currency_rates
      concern: primary_key_unique
      sql: 'SELECT COUNT(*) - COUNT(DISTINCT "rate_day", "src_currency", "dst_currency") AS pk_duplicate_count FROM "acme"."core"."currency_rates"'
      expect: zero
      description: primary_key … must be unique on the physical table.
    - name: fx_rate_coverage__sales_amount_eur
      concern: fx_column_non_null
      sql: 'SELECT SUM(CASE WHEN "eur_conversion_rate" IS NULL THEN 1 ELSE 0 END) AS fx_rate_null_rows FROM "acme"."core"."sales_ledger"'
      expect: zero
      description: normalization_ref requires eur_conversion_rate to be non-null on every row …
```

Fields:

- `name` — snake_case, unique within the contract.
- `concern` — short stable category id (`primary_key_unique`, `fx_column_non_null`). Lets consumers group / filter without parsing names.
- `sql` — single statement returning exactly one row with one column. Use ANSI double-quotes for identifiers; consumers translate per dialect when replaying. Do **not** put dialect-specific syntax here — that belongs in runtime-bound checks, not in the contract.
- `expect` — qualitative outcome of the returned scalar: `true` / `false` / `zero` / `non_zero`.

**Loaders that don't recognize `self_check` MUST ignore it.** Loaders that do recognize it MUST treat assertion failures as warnings unless the consumer explicitly opts into hard-fail. The seeder currently emits two assertion families automatically:

1. `primary_key_unique` per entity with a non-empty `primary_key`.
2. `fx_column_non_null` per metric with `amount_semantics: normalized` + `normalization_ref: fx_column:e.col`.

Both probes would have caught generator-time bugs (PK narrower than declared grain; FX rate gaps silently zeroing normalized SUMs) before they shipped.

Authors should add their own assertions to pin contestable decisions. In particular, when a `count_distinct` identity column was chosen over a materially disagreeing sibling (Workflow step 5), pin the choice so a later replay catches drift — or a regression back to the wrong column:

```yaml
- name: identity_choice__unique_payers
  concern: identity_column_choice
  sql: 'SELECT COUNT(DISTINCT "account_id") > 10 * COUNT(DISTINCT "payer_id") FROM "acme"."core"."payments"'
  expect: "true"
  description: unique_payers counts account_id (the paying customer), not payer_id (the processor executing on the customer's behalf); their distinct counts differ ~800x.
```

## Technical PK vs business key

When both a **surrogate/technical key** (e.g. ingest id) and a **natural business key** exist, treat the natural key as the analytic grain for “one order / one customer” semantics unless the user instructs otherwise; do not equate one technical CDC row with one business entity by mistake.

## Physical fidelity

- Every `entities[].physical` must exist in introspection.
- Every column referenced in PK, grain, joins, metrics must exist on that physical table (or entity column list).
- Do not create bridge entities or fact lines without metadata support.

## After authoring (manual checklist)

1. **Parse**: every listed file loads as YAML with no syntax errors; top-level keys match the sections in this skill.
2. **Cross-references**:
   - Every `metrics[].base_entity` and every `entity_id` in `expression.value`, join `to`, `policies.columns[].selector`, and `vocabulary.dimensions[].selector` matches an `entities[].id` and column names exist on that entity’s `columns`.
   - Every `entities[].physical` still matches what introspection returned (no drift).
3. **Contract root**: `adi_contract_version` is `"1.0"`; `datasource` has exactly the four allowed keys; `defaults` has exactly `timezone`, `currency`, `row_limit`.
4. **Contestable definitions**: every definition from Workflow step 3 has a recorded decision; each metric either sets `allowed_group_bys` or carries a recorded decision to leave grouping open; no group-by is exposed without a supporting key; and every predictable user question listed in step 3 is either answerable through some metric's `allowed_group_bys` or covered by a recorded exclusion decision.
5. **Identity columns**: every `count_distinct` metric's `value` column was verified against the data — candidate identity columns profiled and compared per Workflow step 5; any material disagreement has a recorded decision, both counts in the metric's `scope_note`, and a `self_check` pin (see **Workflow step 5**).

Then run **machine validation** below until clean.

Before you call the contract finished, also confirm:

6. **Departures**: the decisions record opens with "Departures from your documents", and the user has confirmed every item in it, or it says that no document was departed from and no question is open.
7. **Trusted figures**: step 12 ran on the final bundle, and every figure matched or the user decided on each difference, as the decisions record shows; or the decisions record says the user had none.

## Machine validation (required for high confidence)

Human prose in this skill is **not** sufficient to guarantee acceptance. The authoritative check is the MCP validator.

### A. `adi.validate` (structure + semantics + compile dry-run + optional warehouse)

Run **`adi.validate`** — when **`features.core_tools`** is true and **`enabled_tools`** lists it (check **`adi.get_capabilities`**) — on the assembled bundle. It runs structural, cross-document semantic (join graph, reachability, id references), a compile dry-run over every metric and its allowed_group_bys (catches defects only the SQL compiler sees, including aggregation fan-out), and — when you pass **`schema_snapshot_id`** / **`schema_metadata`** — warehouse-alignment checks. Structural and warehouse errors carry a **`path`**; semantic errors carry a **`message`** with the location embedded as a text prefix. Pass the bundle per **Bundle payload shape** above. **Iterate**: fix YAML → re-run **`adi.validate`** until clean. Optionally pass **`apply_repairs`** to get back deterministic **`repaired_documents`** (re-validate those clean, without `apply_repairs`; only when **`features.contract_cache`** is **`true`** does that clean result also return a `contract_hash`).

### B. JSON Schema (offline structural pre-check)

The bundle's formal shape ships alongside this skill under **`schemas/`** — self-contained static files you can run **offline**, with no external tooling or dependency to install, for a quick structural check before (or without) an MCP round-trip. **`adi.validate`** (section A) stays the **authoritative** tool: JSON Schema catches structural/type errors only, **not** the cross-document rules (e.g. entity ids referenced from metrics, join reachability).

- **`schemas/adi_contract_bundle_v1.schema.json`** — validate a **single JSON object** whose top-level keys are the YAML filenames: `contract.yaml`, `entities.yaml`, `metrics.yaml`, `vocabulary.yaml`, and optionally `policies.yaml`, `rules.yaml`. Each value is the **parsed YAML** of that file (native JSON types after `yaml.safe_load`). Assemble that object, then run any **Draft 2020-12**-capable validator.
- **Per-document schemas** (`schemas/contract_document.schema.json`, `entities_document.schema.json`, …) — quick feedback on one file at a time; they do **not** enforce cross-document rules.

### C. Replay `self_check` assertions (MCP + warehouse)

When **`features.execute_sql`** is **`true`** and **`enabled_tools`** lists **`adi.replay_self_check`**, call **`adi.replay_self_check`** with the contract bundle (including **`contract.self_check`** when authored). This executes dialect-translated assertion SQL against the server-configured warehouse — complementary to **`validate`** (which does not run warehouse SQL). Since you have just run **`adi.validate`** on the same bundle, prefer passing the **`contract_hash`** it returned instead of re-uploading `documents` (see **Reuse a validated bundle by hash**). If **`replay_self_check`** is disabled (e.g. the Starter/T1 posture, where `features.execute_sql` is false), rely on **`adi.validate`** and the trusted-figures check (Workflow step 12).

## Anti-patterns (reject)

- Top-level `name` / `version` instead of `title` / `adi_contract_version`.
- `sql_dialect: databricks` (use `spark` for Databricks).
- `sql_dialect: duckdb` (use `postgres` for DuckDB — `duckdb` is an `engine`, not a dialect).
- `grain` as a sentence string instead of a YAML array.
- Policies as a top-level array or wrong key names.
- Policy `classification` outside `pii | sensitive | confidential | public` (e.g. `pii_direct_identifier`).
- Entity-level `description` (or any key outside the strict entity schema).
- Metric `time.canonical` as a bare column instead of a qualified `entity.column`.
- `fx_rules` entries with improvised fields (`stored_direction`, `apply`, …) instead of the documented shape.
- `count_distinct` over an identity column chosen from its name or dictionary phrasing alone when a sibling identity column disagrees materially (actor vs on-behalf-of party; business key vs surrogate/row key).
- Invented tables/joins/metrics not backed by metadata.
- USD-normalized revenue without an FX path.

## Reference

- **Authoring rules**: this skill (prose + checklist).
- **Formal spec + validation**: **`adi.get_authoring_spec`** (the canonical machine-readable spec) and **`adi.validate`** (the authoritative acceptance gate — structure, semantics, optional warehouse alignment).
- **Quality context**: optional dataset/domain documents in the same bundle (see **Agent bundle** above).
- **Strictest acceptance**: **`adi.validate`**, optional **`adi.replay_self_check`** when **`features.execute_sql`** allows warehouse replay, plus optional **schema metadata** for warehouse semantics.

If the agent lacks schemas or the reference validator, use the manual checklist only and warn that **structural** guarantees are weaker. If it lacks **context docs**, the gap is about **meaning**, not structure — do not treat it as a minor caveat: apply the loud warning in **Workflow step 1** (definitions become guesses; numbers stay defensible but are not authoritative).
