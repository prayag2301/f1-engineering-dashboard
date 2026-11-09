# Latest grid inspection and build plan

As of 7 November 2026, the saved archive contains usable models for all eleven constructors, but none is established as the current November race configuration. Prioritize a McLaren São Paulo draft, then Ferrari, Racing Bulls and Red Bull, followed by Audi, Alpine and Cadillac. Mercedes, Williams, Aston Martin and Haas need current reference reconciliation even though they declared no changes at the three weekends checked.

This is a build plan, not a new release or a visual approval. São Paulo runs 6–8 November and is still in progress; use a session-specific observation date until race fitment is established. Mexico City, 30 October–1 November, is the latest completed weekend in this review; Austin, 23–25 October, provides the preceding update package.

**Existing build inspection**

The inspected source is the local bundle selected by `data/pages/snapshot.json`: `pages-2026-09-21-full-grid`. Its archive checksum matches the pin. It contains 17 historical releases and eleven current pointers. Docker is stopped, so these findings do not establish the current contents of the live database or deployed website.

All eleven current GLBs passed `backend/app/services/validation.py::validate_geometry` against the repository's frozen regulation reference: eleven assemblies, embedded materials/textures, valid bounds, orientation, wheelbase and grounded tyres. All 99 current public artifacts matched their SHA-256 and byte counts; all preview images are 1920×1080 and final images 3840×2160. Results and parent release IDs are in [the audit record](../data/references/build-audit-2026-11-07.json).

Front, side, rear and three-quarter contact sheets were inspected for all eleven models. No gross missing assembly or broken silhouette was apparent at contact-sheet scale. The cars retain visibly similar wing, suspension and rear-detail construction; this is consistent with the builder's shared geometry. Body profiles and paint vary, but those variations do not establish contemporary component accuracy. This inspection is not a fresh four-view comparison against November track photography.

| Team / car | Current model observation | Latest reconstruction | Triangles |
|---|---|---|---:|
| Ferrari SF-26 | 23 January launch | 2026.5 detail pass | 205,100 |
| Mercedes W17 | 22 January launch | 2026.5 detail pass | 207,611 |
| McLaren MCL40 | 11 September Madrid | 2026.6 grid | 209,940 |
| Red Bull RB22 | 11 September Madrid | 2026.6 grid | 209,940 |
| Aston Martin AMR26 | 11 September Madrid | 2026.6 grid | 206,550 |
| Alpine A526 | 11 September Madrid | 2026.6 grid | 209,940 |
| Williams FW48 | 11 September Madrid | 2026.6 grid | 206,550 |
| Haas VF-26 | 11 September Madrid | 2026.6 grid, corrected paint | 206,550 |
| Racing Bulls VCARB 03 | 11 September Madrid | 2026.6 grid | 209,940 |
| Audi R26 | 11 September Madrid | 2026.6 grid | 206,550 |
| Cadillac MAC-26 | 11 September Madrid | 2026.6 grid | 209,940 |

**Latest declared changes across all teams**

The following columns summarize the original FIA documents: [Austin, Document 11, 23 October](https://www.fia.com/system/files/decision-document/2026_united_states_grand_prix_-_car_presentation_submissions.pdf), [Mexico City, Document 12, 30 October](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_car_presentation_submissions.pdf), and [São Paulo, Document 12, 6 November](https://www.fia.com/system/files/decision-document/2026_sao_paulo_grand_prix_-_car_presentation_submissions.pdf). Page references below are PDF pages counted from 1, including the cover.

“None” means no update submitted for that event. It does not mean an unchanged setup, identical cars for both drivers, or no developments since the archived model.

| Team | Austin declaration | Mexico declaration | São Paulo declaration |
|---|---|---|---|
| McLaren | Front/rear corner furniture; diffuser | Enlarged cooling louvres | New front wing, rear wing, beam wing; floor furniture |
| Mercedes | None | None | None |
| Red Bull | Front-wing footplate vane; front-corner gaiter | Cooling exits; sidepod/floor junction | None |
| Ferrari | Floor body/boards; sidepod inlet/undercut; diffuser | Rear cooling exit; upper louvres | None |
| Williams | None | None | None |
| Racing Bulls | Front endplate; rear flaps; floor; bodywork shoulder/undercut | Rear cooling exit; louvres | None |
| Aston Martin | None | None | None |
| Haas | None | None | None |
| Audi | Front brake duct; floorboard; mirror stay | Rear brake-duct deflector | None |
| Alpine | Rear floor corner; rear-wing flaps | Exhaust-tailpipe vane | None |
| Cadillac | Forward floor fences; upper cooling louvres | None | None |

Austin and Mexico team pages: McLaren 2, Mercedes 4, Red Bull 5, Ferrari 7, Williams 9, Racing Bulls 10, Aston Martin 12, Haas 13, Audi 14, Alpine 16. Cadillac is Austin page 18 and Mexico page 18. São Paulo: McLaren 2, Mercedes 4, Red Bull 5, Ferrari 6, Williams 7, Racing Bulls 8, Aston Martin 9, Haas 10, Audi 11, Alpine 12, Cadillac 13.

McLaren's [6 November technical briefing](https://www.mclaren.com/racing/formula-1/2026/sao-paulo-grand-prix/the-briefing/) independently confirms new wings and floor components, includes dated practice photography, and describes a return from Mexico's extreme cooling configuration. It supports prioritizing McLaren; it does not supply measured surface dimensions.

**Build scope by team**

These are proposed modeling tasks, conditional on dated photographic evidence. FIA submissions establish reported changes and intended effects, not complete surface geometry or demonstrated performance gains.

| Priority | Team | Assemblies and evidence needed before authoring |
|---|---|---|
| 1 | McLaren | Resolve November front/rear wing sections, supports and floor furniture in close-ups; reconcile Austin corner/diffuser changes. Confirm the reported beam-wing identity and location against images and applicable rules before adding geometry. |
| 2 | Ferrari | Establish a current whole-car reference first: January is too old for an isolated October patch. Then reconcile floor/boards, sidepod inlet and diffuser; retain Mexico cooling as a separate event configuration. |
| 2 | Racing Bulls | Resolve wing endplates/flaps, floor edges and shoulder/undercut together. Check whether Mexico cooling panels were removed for Brazil. |
| 2 | Red Bull | Capture the footplate vane and sidepod-to-floor junction; inspect corner gaiter and cooling outlets. Record optional fitted parts per driver/session. |
| 3 | Audi | Obtain front/rear corner close-ups, floorboard views and mirror-stay views; existing generic ducts are insufficient for these details. |
| 3 | Alpine | Resolve rear floor edge and flap outline, plus exhaust-vane detail. Keep ambient-condition-specific choices attached to their event. |
| 3 | Cadillac | Resolve forward floor fences and louvre placement, then check November retention. |
| 4 | Mercedes | Reconcile the January car against current whole-car photography and intervening declarations; do not relabel the launch reconstruction. |
| 4 | Williams | Compare current bodywork, wings, floor and livery with the Madrid baseline; record unsupported differences as unresolved. |
| 4 | Aston Martin | Compare current inlets, bodywork, wings and floor against Madrid; require session evidence before carrying geometry forward. |
| 4 | Haas | Compare current exterior and cooling fitment with Madrid; retain the accepted corrected-paint parent. |

For each team, collect front, side, rear and three-quarter photographs plus close-ups for changed components. Store the exact image URL, publisher/photographer, capture date, event, driver/session and checksum. Existing team discovery URLs are in `data/references/sources.json`; they are discovery starting points, not accepted November images. The latest complete photographic packages for all teams remain to be assembled.

Backfill declarations and reference evidence between each model's observation and Austin. This review covers the latest three weekends, not the full gap from January/September; the most recent pre-Austin update for teams with three “None” entries remains unresolved. Reconcile retained parts directly against current images rather than assuming every historic upgrade remains fitted.

**Implementation and acceptance sequence**

1. Import the three exact FIA documents through the existing source inbox, retaining publication dates and PDF pages. Match claims to teams/components and mark unsupported shapes as annotation-only. Complete the intervening-history and photographic review before accepting a current configuration.
2. Create dated drafts from the current release IDs in the audit record. Keep Mexico cooling variants separate. Record practice-only fitment explicitly; update the São Paulo evidence cutoff after the event before claiming race specification.
3. Reuse the eleven existing assembly IDs. Proposed ownership: wing changes in `front_wing`/`rear_wing`, boards/fences in `floor`, corner ducts in `suspension`, mirror stays in `chassis`, exhaust detail in `engine_cover`. Check the exact mesh ownership for louvres and bodywork boundaries before declaring revisions. Preserve source claim labels even when multiple claims map to one assembly.
4. Extend only the affected construction in `modeling/build_car.py` and supported values in `modeling/catalog.json`. Current chord/camber and scalar body parameters cannot express every new endplate, duct, fence or louvre topology. Use the existing loft/section helpers; bump the generator for topology changes. There is no explicit named beam-wing implementation in the current builder, so a rear-wing chord adjustment alone cannot represent that claim.
5. Build McLaren geometry first, then four preview views. Compare it with the parent in neutral materials and isolated component views. Test changed-component hashes and require unchanged assemblies to match their parent. Whole-grid checks are necessary if shared helpers change. Body-attached suspension may also change when its supporting body surface changes; declare that dependency explicitly rather than bypassing the history gate.
6. After the pilot passes, build the remaining evidence-ready teams in the order above, one render job at a time by default. Freeze spec, generator, catalog and regulations in new output directories. Use the existing worker/release path for race drafts; `scripts/build_grid.py` currently builds catalog baselines and has no arbitrary per-release spec argument, so rerunning it alone would only reproduce the old configurations.
7. Require a valid GLB and editable scene, hashes for all artifacts, four previews and four 4K renders, successful component-history validation, and recorded comparison against all four reference views. Use `adopt-native` only for matching unfinished drafts when rendering natively. Publish after visual review, then export and validate a new Pages snapshot and run the existing static browser checks for all teams.

The implementation reaches source records, component revisions/specs, the catalog and builder, geometry/history tests, render artifacts and the published snapshot. Existing review UI, ingestion, validation and export paths should suffice; no new rendering framework or frontend feature is planned. Keep historical artifacts immutable and leave current pointers intact until replacement drafts pass.

Success means eleven clearly dated, validated exterior reconstructions with traceable evidence and explicit unresolved surfaces. It does not mean factory CAD, inferred hidden floor geometry, or a proven aerodynamic performance improvement. No model edits, new renders, database imports or publication were performed during this inspection.
