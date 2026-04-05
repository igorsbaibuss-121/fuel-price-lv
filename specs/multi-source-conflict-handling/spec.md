# Stable Multi-Source Fuel Price Aggregation With Conflict Visibility

## Context / Problem

The CLI can already load multiple source inputs in one run, but overlapping records from different sources are not always presented as a stable, easy-to-interpret result set. Users need a way to see a single understandable view of matching station and fuel records while still being able to tell when sources disagree on price.

## Objective

Aggregate overlapping normalized fuel price records from multiple sources into a deterministic result set that preserves source traceability and makes price conflicts explicit.

## Intended User Value

Users can compare Latvia fuel prices across multiple sources without manually spotting duplicate rows. They can still see when multiple sources support the same result and when a displayed price reflects disagreement rather than full agreement.

## Functional Requirements

1. The system must aggregate records only after source-specific inputs have been normalized into the common record shape.
2. Aggregation must consider overlapping records for the same fuel type and likely same station or location across multiple sources.
3. Matching must be deterministic for the same normalized inputs and CLI options.
4. When records are confidently matched, the output must expose one primary aggregated row rather than separate duplicate rows.
5. The aggregated row must preserve source traceability sufficient to identify which sources contributed to it.
6. When contributing source prices are identical, the primary price must reflect that shared value.
7. When contributing source prices differ, the primary price must still be populated and the output must explicitly mark that the row has a price conflict.
8. Conflict visibility must include enough metadata for a user to tell that multiple prices were observed and that the displayed primary price is not the only reported value.
9. If records cannot be matched confidently, they must remain as separate rows.
10. If one or more requested sources fail but at least one source succeeds, the run must still produce results from the successful sources and make the partial failure visible.

## Non-Functional Constraints

1. Existing CLI usage patterns should remain stable.
2. Output changes should be backward-friendly and additive where possible.
3. Aggregation behavior must favor interpretability and safety over aggressive deduplication.
4. The feature must remain suitable for table, CSV, JSON, and report-oriented workflows.
5. Result ordering must remain stable under repeated runs with equivalent successful inputs.

## Edge Cases

1. Two sources report the same station and fuel type with identical prices.
2. Two sources report the same station and fuel type with different prices.
3. Two records partially match on station name but differ enough in address or location text that merging would be unsafe.
4. A source omits address or city fields while another source provides them.
5. More than two sources contribute to the same aggregated row, with a mix of equal and conflicting prices.
6. Only one requested source succeeds.
7. A source returns no rows for the requested fuel type.

## Acceptance Criteria

1. Matching records from multiple sources appear as one stable result row when the match is unambiguous.
2. The aggregated row exposes traceability for all contributing sources.
3. Equal contributing prices produce a non-conflict row with the shared price as the primary price.
4. Differing contributing prices produce a conflict-marked row with explicit conflict metadata.
5. Ambiguous records are left separate rather than merged.
6. Partial source failure does not cancel the whole run when other sources produced valid records.
7. The output contract remains usable for current CLI consumers because new aggregation metadata is additive.

## Out of Scope

1. Reworking source fetch logic or catalog structure.
2. Changing CLI argument names or baseline command semantics.
3. Introducing probabilistic or fuzzy matching that cannot be explained deterministically.
4. Solving non-price data conflicts beyond what is needed to surface price disagreement and source traceability.
