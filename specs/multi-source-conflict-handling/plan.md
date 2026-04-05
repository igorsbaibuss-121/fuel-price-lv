# Implementation Plan: Stable Multi-Source Fuel Price Aggregation With Conflict Visibility

## Technical Goal

Add a deterministic aggregation layer that combines overlapping normalized multi-source fuel price records into a stable result set, preserves provenance, exposes price conflicts explicitly, and keeps current CLI workflows backward-friendly.

## Current State

The repository already supports loading multiple sources in one run and can expose source-level provenance and price-conflict fields in output. Current behavior is driven by CLI flags, but the long-term technical shape should make aggregation rules explicit after normalization and before final output formatting so the behavior stays stable as more live sources are added.

## Proposed Design

Introduce a distinct aggregation step in the result-preparation flow. This step should receive normalized records, apply conservative matching across sources, produce one aggregated record per safe match group, and append explicit provenance and conflict metadata without changing the meaning of non-aggregated rows.

## Aggregation Boundary

Aggregation should happen after all selected sources have been loaded and normalized into the common schema, and before result slicing, output serialization, and report formatting. This keeps source adapters focused on normalization and keeps reporting logic focused on presentation.

## Matching Strategy

Matching should be conservative, deterministic, and based on normalized user-visible fields rather than source-specific identifiers alone. Candidate matching inputs may include normalized station name, normalized address or location text, city, and fuel type. If the available values do not support a clear one-to-one grouping, the records should remain separate.

## Primary Price Rule

If all contributing records for an aggregated row have the same valid price, that value becomes the primary price. If contributing records differ, the primary price should be the minimum valid observed price so the result set remains practically useful while conflict metadata explains the disagreement.

## Conflict Representation

Conflict metadata should be explicit and additive. The aggregated row should preserve enough data to show whether a price conflict exists, what price values were observed, and how large the observed spread is, while also retaining provenance about contributing sources.

## Partial Failure Handling

Failure should be handled at the source level. If at least one requested source returns valid normalized records, aggregation should continue for the successful subset and the run should make the missing or failed sources visible rather than failing the entire command. A full-run failure should occur only when no usable source data remains.

## Output Contract Impact

The preferred approach is additive output evolution. Existing fields should keep their current meaning, while aggregated provenance and conflict details are added as optional columns or properties so current JSON, CSV, table, and report workflows remain usable.

## Validation Strategy

Validate the feature at three levels: aggregation behavior on normalized input groups, CLI-facing output contract coverage for JSON and CSV, and smoke validation for realistic multi-source commands. Validation should cover equal-price matches, conflicting-price matches, ambiguous records that must remain separate, and partial-source failure scenarios.

## Risks and Trade-offs

Conservative matching reduces unsafe merges but may leave some duplicate-looking rows in the output. Using the minimum valid observed price keeps results useful for ranking, but it requires strong conflict visibility so users do not mistake the primary price for unanimous agreement.

## Out of Scope

1. Redesigning importer internals beyond what is needed to provide normalized inputs.
2. Replacing current output formats or CLI flags.
3. Broad source-quality cleanup unrelated to aggregation and conflict visibility.
4. Adding new public data sources as part of this feature.
