# Ingestion Rules

## Evidence Sources

Evidence items are categorized by source type:

| Source Type | Examples | Default Credibility |
|-------------|----------|-------------------|
| Official FIA | FIA technical documents | 0.95 |
| Team announcements | Team press releases | 0.90 |
| Accredited media | Motorsport.com, Autosport, The Race | 0.80 |
| Photography | Trackside photographers, pit lane shots | 0.75 |
| Fan/amateur | Social media, fan sites | 0.40 |
| AI-generated | LLM analysis, computer vision | 0.30 |

## Licensing

All evidence must be tagged with a license:

| License | Usage |
|---------|-------|
| `official` | FIA/team official media, freely usable |
| `cc-by` | Creative Commons Attribution |
| `cc-by-sa` | Creative Commons Share-Alike |
| `editorial` | Fair use for editorial/analysis |
| `restricted` | Cannot be redistributed |
| `unknown` | Default — must be reviewed |

## Credibility Scoring

The confidence score for an upgrade is computed from:

1. **Source credibility** (weight: 0.4) — Average credibility of linked evidence
2. **Photo presence** (weight: 0.2) — Has photographic evidence?
3. **Cross-source agreement** (weight: 0.3) — Multiple independent sources agree?
4. **Quantitative data** (weight: 0.1) — CFD numbers, measurements, timing data?

Final score is capped at 0.95 (nothing is 100% certain until race day).

## Deduplication

Ingestion automatically deduplicates based on:
- Same `team_id` + `race_id` + `component_id` + `description`

When `skip_duplicates=true` (default), matching items are silently skipped.
