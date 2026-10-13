<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Agentic Data Intelligence SA
-->

# Sample Queries - QueryRequest v1 Patterns

Illustrative examples against a fictional `aurora` mobility/subscriptions
contract. Swap the identifiers for your own contract's `metrics.yaml` /
`vocabulary.yaml`.

A few identifiers from that contract:

- Metrics: `net_booking_value_eur` (aliases "revenue", "bookings"), `trip_count`, `monthly_active_revenue_eur`, `cancellation_count`.
- Dimensions: `trips.city_zone`, `riders.home_region`, `trips.trip_state`, `plans.billing_currency`.

## End-to-end (first call)

User: **"Top 5 city zones by revenue."**

1. Resolve intent against the bundle: "revenue" → `net_booking_value_eur` (vocabulary alias); "city zone" → `trips.city_zone`.
2. Call `adi.generate_query` with the request below **and** `contract={"documents": {...}}` (the bundle files as strings). Send `documents` on every call — the hosted service keeps no copy of the contract. (Only where `features.contract_cache` is `true` may later calls pass the returned `contract_hash` instead.)
3. On `ok=true`, answer from `query.explanation` + `query.provenance`; execute `query.sql` only with `query.signature` when execution is enabled.

```json
{
  "query_request_version": "1",
  "metrics": ["net_booking_value_eur"],
  "group_bys": ["trips.city_zone"],
  "top_n": 5,
  "order_by": [{ "field": "net_booking_value_eur", "direction": "desc" }]
}
```

## Success patterns

### Metric + dimension + relative time

**Prompt**: "What was net booking value last quarter by region?"

```json
{
  "query_request_version": "1",
  "metrics": ["net_booking_value_eur"],
  "group_bys": ["riders.home_region"],
  "time_range": {
    "type": "relative",
    "value": "last_quarter",
    "as_of": "2026-05-05"
  }
}
```

`as_of` anchors the relative window; set it to the user's current date.

### Filter — equality on a dimension

**Prompt**: "Monthly active revenue for plans billed in GBP only."

```json
{
  "query_request_version": "1",
  "metrics": ["monthly_active_revenue_eur"],
  "filters": [
    {
      "entity_ref": "plans.billing_currency",
      "operator": "=",
      "value": "GBP"
    }
  ]
}
```

### Filter — date range (non-canonical column)

**Prompt**: "Cancellation count where cancelled_at is on or after 2026-01-22 and before 2026-04-23."

```json
{
  "query_request_version": "1",
  "metrics": ["cancellation_count"],
  "filters": [
    {
      "entity_ref": "cancellations.cancelled_at",
      "operator": ">=",
      "value": "2026-01-22"
    },
    {
      "entity_ref": "cancellations.cancelled_at",
      "operator": "<",
      "value": "2026-04-23"
    }
  ]
}
```

## Refusal and clarification patterns

Recover from `refusal.details` (see [../references/refusal_codes.md](../references/refusal_codes.md)).

- **Unknown metric** → `metric_not_found`. Offer `details.available_metrics` / `details.candidates`.
- **Disallowed dimension** → `dimension_not_allowed`. Switch to a `details.allowed_group_bys` selector.
- **Policy denial** → `policy_denied`. Provide safe aggregate alternatives; never expose the blocked column.

## Workflow reminder

1. Call **`adi.get_capabilities`**; note `features.execute_sql` and `enabled_tools`.
2. Resolve user intent to canonical ids via `vocabulary.yaml` / `metrics.yaml`, then build a **`query_request` v1** object.
3. Call **`adi.generate_query`** with `query_request` + `contract` (`documents` on every call; `contract_hash` only when `features.contract_cache` is `true`).
4. If `ok=true`, surface `warnings` when present; call **`adi.execute_sql`** only when `query.signature` is present and capabilities allow — unsigned SQL never runs on MCP. Pair `result.rows` with `query.provenance` and `query.explanation` in the answer.
5. If `ok=false`, branch on `refusal.code` + `refusal.details` and retry once with a safe alternative.
