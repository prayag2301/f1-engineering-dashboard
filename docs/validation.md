# Local implementation validation — 12 September 2026

This records checks performed on the local Apple M1 Mac. It distinguishes executable checks from the maintainer's visual acceptance. No actual car configuration has been published.

## Application and data

The canonical application is `frontend/` plus `backend/`. Compose uses the same implementation as the root development commands. PostgreSQL, Redis, migration, API, web, scheduler, and native ARM64 Blender worker containers were exercised locally.

An isolated empty PostgreSQL database completed migrations 001–003 and bootstrap twice without duplicate baselines. A separate copy of the existing database completed the additive migration with legacy IDs and values preserved, apart from the intended normalization of enum labels. PostgreSQL triggers rejected mutation of immutable evidence, component revisions, and published snapshots. The original database was backed up to `data/backups/before-reviewed-releases.dump` before its migration. The two final ready drafts, 22 component revisions, three source documents, ten draft claims, and their build/audit records were then imported. Checksums of all ten legacy tables matched before and after handover, including IDs. PostgreSQL and the worker container were recreated, and both complete releases validated again from the persistent volumes.

## Automated checks

| Check | Observed result |
|---|---|
| Python API, evidence, scheduling, and history suite | 104 tests passed; 11 existing Pydantic configuration deprecation warnings |
| Next.js production build, TypeScript, ESLint | Passed |
| Browser workflows against the production image | Five passed: comparison/camera synchronization, asset failure/retry, rapid team switching, mobile/keyboard controls, authenticated review sign-in/out |
| Native Blender geometry smoke | Ferrari and Mercedes exports passed; a Ferrari front-wing camber revision changed only that assembly's surface fingerprint |
| Real-artifact history integration | Two publications in the separate `f1_acceptance` database; annotation-only build preserved all 14 reusable artifacts byte for byte; rollback retained both immutable versions |
| Live evidence import | An 18-page FIA Spanish GP car-presentation PDF produced 10 draft component claims, including Ferrari suspension and Mercedes rear-wing claims |
| Failed artifact and retry integration | A corrupted copied test GLB caused build failure without changing the current pointer; authenticated retry succeeded on attempt two after restoring the fixture |
| Scheduler recreation | Persisted Monday schedule key retained; no duplicate catch-up job |
| Canonical HTTP and real-model checks | All 30 artifacts passed authenticated GET/HEAD and SHA-256 checks; public access to drafts was denied; clicking the real mesh selected the nose and switching teams loaded the correct car |
| Native Mac orbit benchmark | Final Mercedes mesh, Apple M1 Metal, 1920×1080 drawing buffer, 440 rendered frames in 8.0052 seconds: **54.96 FPS** |

The browser suite uses explicitly synthetic public manifests to exercise history without publishing the real drafts. The real-artifact integration test uses a separate database and asset directory, and its synthetic review booleans are not copied to the application. The benchmark previews a real draft within one authenticated browser; it does not alter publication state. Performance varies with viewport, device load, and hardware.

The canonical scheduler also completed its first catch-up collection: it recognized the FIA PDF as a duplicate and preserved all existing drafts. Ferrari’s news index returned HTTP 403; that partial coverage is visible in Jobs & history and supports manual text import. The other configured indexes/feeds were reachable but returned no matching new technical stories in that run.

The source tests cover duplicate stories, multiple teams/components, absent publication dates, unresolved events, conflicting evidence, blocked retrieval, feed dates, and failed collection. Workflow tests cover one Monday catch-up after downtime, Berlin daylight-saving boundaries, stale worker leases, retries, authorization, failed artifact validation, and annotation-only geometry reuse.

Software-WebGL browser checks can time out under simultaneous CPU rendering and compilation. The test configuration allows additional startup time and provides an optional native Metal path on macOS; the measured performance result uses Metal. Hosted AMD64 verification now passed in [Application checks](https://github.com/prayag2301/f1-engineering-dashboard/actions/runs/34706933264): both baselines exported successfully and the revised front wing left all ten other assemblies unchanged. Binary GLB sizes differ slightly between ARM64 and AMD64 exports; triangle counts and validation invariants agree.

## GitHub Pages export

The `codex/github-pages-release` branch adds a static export independent of the
Docker runtime. The export and snapshot tools passed 12 tests for published-only
content, review requirements, corrupt and missing artifacts, unsafe archive
entries, complete history, deduplication, and rollback pointers. The actual local
API rejected a deployment export because neither baseline has been published.

Four static browser tests passed on this Mac: direct subpath routes and refreshes,
no API or credential requests, exported asset checks, populated comparison with
synchronized cameras, rapid switching, mobile/keyboard access, and archive retry.
Populated browser data is explicitly synthetic and exists only in intercepted
test requests; it never changes the site build or local publication state.
The patched static build also passed these checks with the actual 149,518-triangle
Mercedes GLB substituted into the isolated browser fixture.
The static JavaScript excludes the maintainer UI. Both static export and the
standard standalone build are validated separately in CI.

The first [Pages workflow](https://github.com/prayag2301/f1-engineering-dashboard/actions/runs/34706933287) passed its build and browser checks, uploaded a static artifact, and skipped deployment as intended. The new branch is allowed by the `github-pages` environment and selected by `PAGES_DEPLOY_BRANCH`.

The deployed `demo/static` site remains the handover fallback until both reviewed
baselines are pinned and the replacement workflow can deploy. See
[the Pages guide](github-pages.md) for snapshot upload and rollback.

Next.js and its lint configuration were updated from 14.2.15 to 14.2.35 for the
[14.x RSC denial-of-service patch](https://nextjs.org/blog/security-update-2025-12-11).
This is not a clean dependency audit: npm still reports advisories in the existing
Next 14/tooling dependency tree. A supported-major framework and renderer upgrade
remains separate work before exposing a Next.js server publicly. Pages serves
exported files, and the Docker web service stays bound to 127.0.0.1.

## Geometry and provenance

| Draft | Configuration date | Triangles | GLB bytes |
|---|---|---:|---:|
| Ferrari SF-26 | 23 January 2026 launch | 144,062 | 3,914,988 |
| Mercedes W17 | 22 January 2026 launch | 149,518 | 4,034,860 |

Each car contains eleven named assemblies, component-local anchors, packed original carbon texture, and painted-body, rubber, carbon, and metal materials. Exports use metres, Y-up, and nose toward −Z. Geometry checks verified a 3.4 m wheelbase, four grounded tyres, longitudinal nose, body bounds, materials, and GLB integrity.

Build outputs include the editable scene, exact builder/catalog/regulation snapshot, component fingerprints, GLB, four 1920×1080 previews, and four 3840×2160 PNGs. Delivery renders use Cycles on CPU with 64 samples and adaptive sampling. Subsequent builds default to 128 samples; `RENDER_SAMPLES` is configurable. Debian's ARM64 Blender build lacks OpenImageDenoise, so these renders retain visible sampling noise.

These are authored exterior estimates based on dated launch references. The later FIA submission establishes reported component changes; it has not been used to invent dimensions or silently change either launch car. Its publication date and observation dates remain unresolved in the inbox. The supplied reference set records FIA Section C issue 20 and a limited set of dimensional constraints; it is not a complete compliance check.

## Visual acceptance remains with the maintainer

The four draft views should be compared with dated front, side, rear, and three-quarter photographs in the review studio. All visual-acceptance checkboxes remain unchecked. Exact surface curvature, small aero details, suspension pickup positions, and hidden geometry remain approximations; sponsor and tyre graphics are omitted. Build validation does not certify a factory-accurate or photorealistic replica.

The implementation supports further baseline modeling passes before first publication through **Build revised baseline**. For later releases, confirmed reports with insufficient shape evidence remain annotation-only. Supported geometry revisions preserve all unchanged assemblies; circuit-specific configurations and reversions retain their own evidence and history.

The running review studio is **http://127.0.0.1:3000/review**. Use the local `ADMIN_TOKEN` from `.env`. An unrelated application owns this Mac’s IPv6 `localhost:3000` address, so the explicit IPv4 address is used. Saved previews, 4K perspective downloads, the review screenshot, benchmark result, and validation logs are under the ignored `data/releases/` directory.

See [the operating instructions](../README.md) and [modeling notes](../modeling/README.md) for reproduction and the review workflow.
