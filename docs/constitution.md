# Engineering Constitution

This repository is a small Python CLI for Latvia fuel price aggregation. Future work should keep the CLI understandable, runs reproducible, and multi-source behavior easy to interpret when sources disagree.

## 1. Product Clarity and Understandable Output

CLI output must stay readable to a user who is comparing station prices, not inspecting internal processing details. New fields are acceptable when they improve interpretation, but the primary result should remain easy to scan in table, CSV, and JSON output.

## 2. Reproducible CLI Execution

The same input sources and CLI arguments should produce the same logical result set, except where a live source genuinely changes upstream data. Features that depend on unstable ordering, hidden defaults, or implicit local state should be avoided.

## 3. Stable Data Contract

Normalized records and user-facing output fields are a project contract. Prefer additive changes over breaking renames or removals, and make any new metadata explicit so downstream consumers can keep working.

## 4. Safe Source Integration

Each input source must be treated as untrusted and potentially incomplete. Source-specific behavior should not weaken validation, and ambiguous cross-source matches should stay separate rather than being merged unsafely.

## 5. Readability Over Cleverness

Implementation should favor direct, reviewable logic over compact but opaque transformations. Deterministic behavior is more important than clever heuristics, especially in matching, deduplication, and reporting flows.

## 6. Documentation as Part of Delivery

Behavioral changes are not complete until the repository documentation explains what changed, when to use it, and what guarantees still hold. Specs, plans, and tasks should reflect the real feature intent, not placeholder process text.

## 7. Test and Smoke Validation Required

Changes that affect aggregation, reporting, or CLI output must include automated coverage for the expected behavior and a smoke check for the end-to-end command path. Validation should prove both the happy path and the most likely failure conditions.

## 8. Explicit Failure Visibility

Failures must be visible enough that a user can tell whether the run succeeded fully, partially, or not at all. Silent data loss, swallowed source errors, or hidden conflicts are not acceptable for a price aggregation tool.
