# Weekly updates

Two supported intake paths collect new evidence for all eleven constructors. Neither treats a new photograph or news story as proof of a new aerodynamic surface.

## Local automatic inbox

Run `docker compose up -d --build` and keep Docker running. The existing scheduler creates one durable collection job per week, due Monday at 10:00 Europe/Berlin. It catches up after downtime, handles daylight saving time, and retries failed collection twice after 15 and 30 minutes. The database deduplicates unchanged articles. Source failures remain visible in the review studio job results.

`data/references/sources.json` controls FIA submissions, technical publishers and constructor sites. Discovery filters unrelated sports, external navigation and duplicate links. All eleven constructors and their chassis identifiers are recognized; passages mentioning multiple teams remain unresolved. Image references accompany imported documents. Websites requiring JavaScript or rejecting automated access need manual URL/text review and are reported as incomplete coverage.

To collect immediately:

```sh
python3 scripts/fetch_upgrades.py
```

## Collection while the Mac is off

`.github/workflows/weekly-references.yml` runs Monday at 08:00 UTC and can also be started manually. It installs the backend dependencies, collects a report without database access, attaches Markdown to the run summary and retains the JSON/image-link artifact for 90 days. It has read-only repository permissions and needs no account secrets. **The hosted schedule activates only after this workflow reaches the repository's default branch.** GitHub schedules can be delayed; they are not an exact-time service. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Run the same report locally:

```sh
backend/.venv/bin/python scripts/weekly_report.py \
  --output data/weekly/2026-09-28 \
  --previous data/weekly/2026-09-21-verified/report.json
```

`--previous` detects changes to article text or image URLs. Without a previous report, all discovered references are marked new; importing them into the local database still deduplicates unchanged articles. Undated sources are explicitly marked unknown rather than assigned the retrieval date. Reports use a 14-day lookback for dated articles. All-source failure exits nonzero after saving diagnostics; partial coverage remains visible in the report.

To import a downloaded report:

```sh
docker compose run --rm --no-deps \
  -v "$PWD/data/weekly:/weekly:ro" \
  api python -m app.cli import-weekly /weekly/2026-09-28/report.json
```

This fetches each changed URL through the normal publisher allowlist and creates review candidates. It does not trust report text as a model instruction.

## From evidence to dashboard

1. Review the source date, event, constructor and component in `/review`.
2. Keep claims with insufficient shape evidence as annotations. For visible changes, author component parameters or a new generator revision and record uncertainty.
3. Build the new configuration, compare front/side/rear/three-quarter renders to the linked images, then publish. Failed collection or builds leave current releases intact.
4. Export the public archive with `scripts/pages.py export`; validate it and build/test Pages before selecting a new snapshot pin.

Future automation should generate proposed component revisions plus image comparisons for review. Automatic deployment can follow a reviewed snapshot, but an unattended image-to-CAD step cannot establish hidden geometry, dimensions or whether a part is an actual upgrade.

## First live check

On 21 September 2026 the initial report discovered 29 references and recorded 15 retrieval/extraction errors. This led to tighter sport/path filtering, corrected Williams and Racing Bulls sources, and explicit reporting for empty indexes. A second run found 35 references with 15 explicit failures/empty indexes. The local `data/weekly/` reports retain the detailed coverage; they are generated output, not checked-in source data.

The first durable local weekly job (`weekly:2026-09-21`) also completed on its
first attempt: 33 documents, 81 draft candidates and 15 explicit access/extraction
errors. These candidates are unverified review material, not published upgrades.
