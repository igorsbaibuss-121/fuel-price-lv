# Tasks: Stable Multi-Source Fuel Price Aggregation With Conflict Visibility

## Ordered Tasks

1. Identify the exact point in the current workflow where all selected source records are already normalized and not yet formatted for output, and record that as the aggregation insertion point.
2. Introduce a dedicated aggregation layer that operates on normalized multi-source records and returns a stable result set for downstream filtering and reporting.
3. Define and apply a conservative matching rule using normalized station name, normalized address or location text, city, and fuel type, with deterministic grouping behavior.
4. Ensure ambiguous candidate matches are kept as separate rows instead of being merged into a shared aggregate.
5. Implement deterministic primary price selection so equal contributing prices keep their shared value and differing prices select the minimum valid observed price.
6. Add explicit aggregation metadata for provenance, including all contributing sources and the count of contributing sources.
7. Add explicit conflict metadata for differing observed prices, including a conflict indicator, the observed price set, and spread-oriented summary fields.
8. Preserve backward-friendly output behavior by keeping current fields stable and exposing aggregation metadata as additive output fields in table, CSV, JSON, and report workflows where applicable.
9. Handle partial-source failure so successful sources still produce results, while failed sources are surfaced clearly and a total failure happens only when no usable source data remains.
10. Add unit coverage for unambiguous matches, identical-price groups, conflicting-price groups, ambiguous records that stay separate, and partial-source failure behavior.
11. Run smoke validation for representative multi-source CLI commands, including deduplicated and conflict-visible output paths, and confirm result ordering and report generation remain stable.
12. Update README documentation later, during implementation delivery, to describe the user-facing aggregation and conflict-output behavior without changing CLI semantics.
