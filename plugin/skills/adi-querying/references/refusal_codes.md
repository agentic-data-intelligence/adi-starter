<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# ADI - Refusal Code Playbooks

Refusal handling for `adi.generate_query`. A refusal is `{ok: false, refusal: {code, message, suggestion, contract_path, details}}`.

## Core principles

- Treat refusals as expected control flow, not errors.
- Recover from `refusal.details` — it carries the valid options (available metrics, allowed group-bys, candidates) so you can retry with a contract-backed request instead of guessing.
- Use contract-backed alternatives; never invent metrics or dimensions.
- Retry at most once with a safer request.

## Refusal codes

The `details` column lists the keys present on `refusal.details` for that code — use them to recover.

| Code                             | Meaning                                                                                                                | `details` keys                                                                      | Recovery                                                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `request_malformed`              | Invalid `query_request` shape/values                                                                                   | `path`, `expected`                                                                  | Fix the field at `path` to match `expected`                                                    |
| `spec_version_unsupported`       | `query_request_version` not supported                                                                                  | `requested_version`, `supported_spec_versions`                                      | Resend with a supported version                                                                |
| `metric_not_found`               | Metric not in contract                                                                                                 | `metric_id`, `available_metrics`, `candidates`                                      | Offer `available_metrics` / `candidates`; ask user                                             |
| `metric_ambiguous`               | Metric phrase matched more than one                                                                                    | `matches`, `candidates`                                                             | Ask user to pick from `matches`                                                                |
| `entity_not_found`               | Unknown entity in a ref                                                                                                | `entity_ref`, `source`, `available_entities`, `candidates`                          | Use a valid entity from `available_entities`                                                   |
| `field_not_in_contract`          | Unknown column on a known entity                                                                                       | `entity_ref`, `source`, `available_columns`                                         | Pick a column from `available_columns`                                                         |
| `dimension_not_allowed`          | Group-by not permitted for the metric                                                                                  | `metric_id`, `entity_ref`, `allowed_group_bys`, `candidates`                        | Switch to an `allowed_group_bys` selector                                                      |
| `dimension_disallowed`           | Group-by explicitly blocked                                                                                            | `metric_id`, `entity_ref`, `reason`                                                 | Remove the blocked dimension                                                                   |
| `policy_denied`                  | Policy restriction (PII/governance)                                                                                    | `policy_id`, `entity_ref`, `safe_alternatives`                                      | Offer aggregated/masked alternatives                                                           |
| `join_path_absent`               | Metrics not safely joinable                                                                                            | `metric_ids`, `reachable_entities_per_metric`                                       | Split the request or pick compatible metrics                                                   |
| `time_grain_unsupported`         | Requested time grain unavailable                                                                                       | `metric_id`, `requested_grain`, `supported_grains`                                  | Use a grain from `supported_grains`                                                            |
| `aggregation_invalid`            | `order_by.field` not in metrics/group_bys                                                                              | `field`, `valid_fields`                                                             | Order only by a field in `valid_fields`                                                        |
| `high_cardinality_refused`       | Group-by would explode row count                                                                                       | `entity_ref`, `cardinality_estimate`, `safe_alternatives`                           | Add filters, use `top_n`, or pick a `safe_alternatives` bucket                                 |
| `currency_normalization_missing` | Monetary metric lacks an FX path                                                                                       | `metric_id`, `currency_code`, `missing_window`                                      | Use a local-currency metric or narrow `missing_window`                                         |
| `aggregation_fanout`             | Additive metric over a to-many join                                                                                    | `metric_id`, `aggregation`, `join`, `cardinality`, `safe_alternatives`              | Use a count_distinct metric or a to-one dimension                                              |
| `contract_invalid`               | The contract itself cannot compile                                                                                     | `entity_ref`, `reason`, `safe_alternatives`                                         | Fix the contract (run `adi.validate`); not a request problem                                   |
| `contract_not_cached`            | `contract_hash` unknown to server, or contract caching disabled (`details.contract_cache: false` — the hosted default) | `contract_hash`, `contract_cache` (present, `false`, only when caching is disabled) | Re-send `contract.documents` to re-upload; if `contract_cache` is `false`, stop sending hashes |
| `intent_unparseable`             | Request could not be interpreted                                                                                       | `reason`                                                                            | Rebuild a valid `query_request` v1                                                             |
| `unsafe_operation_denied`        | Requested operation is blocked                                                                                         | `operation`, `reason`, `safe_alternatives`                                          | Offer a `safe_alternatives` option                                                             |
| `unsafe_sql_denied`              | SQL failed safety checks                                                                                               | `reason`                                                                            | Do not retry raw SQL; regenerate via the contract                                              |

## Clarification responses

Some ambiguous inputs return candidate lists (e.g. `metric_ambiguous.matches`, `*.candidates`) instead of a hard failure. When present, surface the options and ask the user to choose rather than picking silently.

## Connection failures

If `adi.*` tools are unavailable:

1. Verify MCP server connectivity.
2. Confirm authentication — re-run the client's MCP OAuth login (e.g. `claude mcp login adi`) if the session expired.
3. Report the issue; do not fall back to handwritten SQL.
