# Made-in-China background enrichment — Canton Fair October 2026

These artifacts enrich all 30,207 source positions from `Result/Exhibition Organizers/cantonfair/cantonfair_Oct2026.csv` using Made-in-China’s public supplier-name search and publicly displayed company profiles.

## Outcome summary

| Outcome | Count |
|---|---:|
| `extracted` | 4,301 |
| `no_exact_supplier_match` | 22,763 |
| `identity_mismatch` | 1,361 |
| `ambiguous_exact_supplier_match` | 1,781 |
| `missing_source_company_name` | 1 |
| `request_error` | 0 |

A profile is attributed only where both the public search result and the resolved profile company heading are exact normalized matches to the Canton Fair source name. Empty/unavailable requested source sections are recorded as `source_omitted`; they are not inferred.

The CSV and JSON contain equivalent 30,207-row datasets. The local per-profile checkpoint is intentionally not published because it is run-state rather than a final result artifact.
