<!-- BEGIN F1 BLENDER STRUCTURE REFERENCE -->
# F1 Blender construction reference and implementation plan

Scope: this reference applies only to this F1 engineering dashboard repository and its descendants. It is project guidance, not global Codex guidance.

Inspected 2026-11-10, generator 2026.9, repository baseline 63086fd. This is a proposed future structure, not an implemented migration or a declaration that drafts are approved. Recheck code and current evidence before implementation. Follow the user's current task; this reference does not independently authorize publication, new work, or unattended execution.

Implementation status (2026-11-10): generator 2026.10 implements the first wing-control increment: optional camber-peak stations and endplate shoulder rails for two pilots, with frozen helper validation. The remaining passes below are planned work. See `modeling/README.md`; publication and full-build timing remain separate gates.

Local Docker Review Studio now uses token-free `LOCAL_REVIEW_ACCESS`; keep its host port bound to loopback.

## Decision

Add more meaningful shape controls and construction surfaces, rather than uniformly adding polygons. A control section changes the shape; tessellation merely samples that shape more finely. Use physical attachment landmarks and evidence-backed subparts as the starting structure. Keep the existing Python/Blender generator, eleven assembly IDs, component history, frozen builds, and review/publication gates. Start with front wing and visible diffuser; do not replace the whole system with a CAD framework or Geometry Nodes graph.

Accuracy order: dated evidence and camera alignment → silhouette/proportion → surface curvature and junctions → visible mechanical detail → material response → image noise and delivery performance. Extra samples cannot correct a wrong silhouette, and extra bolts cannot correct a generic surface.

## Current pipeline, inspected by stage

| Stage | Current implementation | Realism limitation / consequence |
|---|---|---|
| 1. Evidence and authoring | Sources and review services feed component revisions; `modeling/catalog.json` stores team profiles and parameters. | Reference records do not automatically become calibrated shape constraints. Authored dimensions remain estimates. Two pilot teams have explicit wing profiles; many other shapes use shared fallback construction. A dated label does not independently prove race fitment. |
| 2. Freeze and queue | `backend/app/tasks.py::build_version` freezes spec, builder, catalog, regulations; runs a leased Celery job. Annotation-only versions reuse parent artifacts. | Good reproducibility foundation. A modeled revision rebuilds the complete scene. Runtime build settings and executable identity need a richer frozen record. A future split into Python modules must freeze the entire dependency closure, not just `build_car.py`. |
| 3. Primary geometry | `build_car.py` uses lofts, sectional airfoils, ruled skins, boxes, rods, tubes and an evaluated cockpit Boolean. | Much dense geometry has relatively few independent shape controls. Ferrari/non-Ferrari branches remain in floor/diffuser/body construction. Smooth shading is broadly applied, which can blur the visual distinction between laminate edges and rounded panels. |
| 4. Wing geometry | `station_sample`, `sectional_wing`, `wing_point`, `ruled_skin`, `build_front_wing`, `build_rear_wing`; 2026.9 adds rolled edges, footplate crown, pylon shoes. | Sectional wings use the same analytic section family and fixed tessellation; endplates start as interpolation between two rails, with global roll/crown values. These cannot independently describe every local twist, shoulder, return and edge radius. Several supports are surface-derived, but some mount locations remain fixed. |
| 5. Floor/diffuser | `build_floor` shapes the upper floor; the inline diffuser block in `build_car` constructs a five-station longitudinal ramp, constant ±0.51 m width, and walls at fixed X positions. | A cross-car straight ramp and fixed partitions provide little control over local outlet shoulders, spanwise curvature, wall sweep, or the floor/outlet transition. Concealed channels are generic estimates and must not be promoted to factual aerodynamic detail. |
| 6. Detail/materials | Open rims, rotors, controls and hardware; generated twill base-color texture; `uv_project` applies the same projection to mesh objects. | The weave primarily varies color, rather than surface-normal/roughness response. Uniform projection is poorly matched to curved panel flow. Some small features are approximate solid proxies; excessive mesh detail can add draw calls without improving normal viewing distances. |
| 7. Export/source | One geometry scene is exported as GLB with applied modifiers; component hashes are computed; curves are converted before the editable scene is saved. | Browser and studio share dense geometry, with no explicit delivery-mesh tier. `source.blend` preserves meshes and surviving modifiers, but not all original curve authoring controls. Material hashing currently covers selected BSDF inputs and images, not every potential future normal/roughness-node configuration. |
| 8. Rendering | Cycles CPU in Docker; optional native Metal; 160 worker samples, adaptive threshold 0.035, fixed seed and studio views. Denoising is capability-gated. | Preview and 4K are interleaved per view. The worker's final validation follows the full render run; private previews provide early inspection but do not pause final rendering. On the Debian ARM image, absent OIDN cannot be fixed by just toggling denoising. |
| 9. Browser | `CarViewer.tsx` uses Three.js ACES tone mapping, environment lightformers, demand rendering, DPR up to 1.5; studio uses AgX. | Lighting, tone mapping and shading are not identical between browser and Blender. More accurate studio materials may still look different in the deployed viewer. |
| 10. Validation/publication | Geometry smoke checks, component-history hashes, artifact checksums/dimensions, four-view review, immutable releases, pinned Pages archive. | These gates establish structural validity and provenance, not photographic similarity. Wing gap tests sample rays and attachment anchors; they are not exhaustive collision tests. Existing asset checks do not establish a noise/aliasing quality threshold. Code deployment does not publish draft meshes. |

Evidence locations: `modeling/build_car.py`; `backend/app/tasks.py`; `backend/app/geometry_check.py`; `backend/app/services/{releases,validation}.py`; `frontend/src/components/CarViewer.tsx`; `infra/docker/Dockerfile.worker`; `scripts/{build_grid,render_wing_review}.py`; `data/references/realism-validation-2026-9.json`. Function names are more durable references than line numbers.

## Target construction structure

Keep a small, explicit sequence inside the existing builder first:

1. **Resolved configuration**: team, observed event/session, source IDs, uncertainty, parent revisions and generator identity. Freeze exact effective parameters, including fallback selections.
2. **Construction controls**: named landmarks, boundary curves and section stations in metres. Store authoring controls separately from tessellation settings. These controls guide construction; they are not extra rods to show inside the finished car.
3. **Primary surfaces**: lofts/patches for wing elements, endplates, floor and diffuser boundaries. Match visible silhouettes and gaps before small detail.
4. **Junctions and thickness**: connected surface returns, explicit root transitions, local radii, edges and true openings. Derive adjacent parts from common boundary data.
5. **Visible secondary parts**: brackets, hinges, supports and fasteners attached using surface coordinates or evaluated normals, not independent world-coordinate guesses.
6. **Materials/UVs**: named material regions, physical texture scale, tangent-space normal and roughness detail where appropriate.
7. **Delivery/export**: initially retain one geometry representation. Introduce a separate browser mesh only if profiling shows a need; preserve assembly ownership and visible openings.
8. **Cheap validation and neutral review**: export, test and inspect before expensive final stills.
9. **Final rendering, release validation and publication**: complete artifacts, reviewed references, browser checks, frozen manifest, then normal publication and Pages export.

For future module extraction, use only `build_car.py` as entry point, shared surface utilities, and front-wing/diffuser component modules when those components are genuinely large enough. First update worker/native freezing, Docker COPY paths, imports, adoption validation, manifest asset rules and tests. Existing validation assumes flat artifact filenames; do not introduce nested frozen paths without changing and testing those rules. Prefer freezing an explicitly enumerated flat set of helper files over building a general plugin loader. Do not break old frozen releases.

## Front-wing implementation design

**Control structure:** define independent left/right symmetry policy; mainplane and flap IDs; span stations at the nose root, mid-span, start of outboard transition, flap tip and endplate junction. Add stations only at observed curvature/planform changes. Each section should support leading/trailing positions, chord, incidence/twist, camber position and thickness distribution. Begin by extending the existing station representation compatibly; add explicit normalized upper/lower section curves only for sections that the current analytic formula cannot represent. Optional point arrays require monotonic sampling and finite-value validation.

**Endplate:** replace a single two-rail interpolation, for evidence-ready pilots, with a small patch/cage bounded by front edge, rear edge, upper rolled edge and foot junction. Add an intermediate shoulder rail to control cross-surface curvature. Keep top-edge roll radius and spanwise sweep locally adjustable. Use continuous shared boundary samples to meet the footplate. Preserve actual laminate thickness and intentional sharp edges; do not soften the entire part with blanket subdivision.

**Flap-to-endplate and root transitions:** make edge curves explicit. Flap termination, nose-root clearance, slot openings, bracket points and junction fillets should derive from the same resolved surfaces. Avoid independently hardcoded attachment coordinates. Use bounded surface coordinates (span fraction, chord fraction, signed normal offset) with deterministic IDs for supports. Changing chord/sweep/camber must update brackets without closing gaps.

**Useful added geometry:** local loops near rolled lips, flap tips, sharp curvature transitions, bracket feet and visible junctions. For example, trial additional control stations at an outboard kink, not a uniform doubling of all 72 span samples. Choose tessellation by measured screen-space error at agreed close-up cameras; keep deterministic sampling settings in the frozen build.

**Review gate:** neutral front/oblique/endplate-detail views plus complete-car context; no impossible intersections, no unintentional seam opening, no visibly detached bracket; unchanged non-wing hashes; distinct pilot contours supported by reference images. Differences in hashes alone are insufficient evidence of accurate team differences.

## Diffuser implementation design

Extract the current inline block into `build_diffuser(team, parameters, carbon, floor_boundary)` without changing geometry first. Prove baseline hash equivalence before authoring new shapes.

**Control structure:** define visible inlet boundary, longitudinal rise stations, outlet boundary, left/right outer wall rails and centerline. Add several cross-car control points per station so width and height can vary independently across the outlet. Represent each visible channel divider by its own centerline/sweep, upper contact curve, lower boundary, thickness and termination. Permit different visible divider counts only when supported by evidence; do not assume the present five walls are correct for every car.

**Shared floor interface:** derive the diffuser inlet and attachment regions from a shared resolved floor/diffuser interface. Do not just add more faces to the ramp. Clarify ownership: floor owns the upstream boundary, diffuser owns downstream expansion and outlet walls. A floor change that alters attached diffuser geometry must declare both component revisions. Preserve unrelated assemblies; legitimate dependencies are not a reason to bypass history validation.

**Useful added geometry:** outlet shoulder patches, varying-width ramp sections, wall-root fillets, swept visible strakes, trailing laminate returns and local edge radii. The exact shapes and counts are authored from photos. Where underside references are unavailable, retain a minimal explicitly uncertain enclosure; do not invent hidden tunnels, internal stiffeners or performance claims to make the model look complex.

**Review gate:** add rear-low, underside-oblique and isolated diffuser cameras to the fixture; include the floor connection in a context view. Check ramp continuity, width/height progression, floor connection, strake seating, ground clearance, and self-intersections. Closed laminate meshes need valid orientation/manifold tests; intentional open channels must stay open. Use per-feature tolerances based on scale; the existing 4 mm wing-contact threshold is not a blanket realism tolerance.

## Materials, shading and browser delivery

First make panel-appropriate UVs for the pilot assemblies. Align carbon weave to authored laminate regions at a documented scale; use a restrained tangent-space normal map and roughness variation instead of only changing base color. Keep real geometry for silhouettes, slots and openings. Reserve baked detail for weave, shallow scratches and details too small to change visible silhouettes. Bake only maps that survive the supported glTF material path. Record colorspaces and texture dimensions; inspect UV seams and tangent-space shading in the browser.

Extend material fingerprints to include the actually exported normal/roughness/occlusion maps and relevant scalar/node settings. Add a negative history test: changing normal strength or a texture must invalidate affected component fingerprints. Preserve old fingerprint schemes by recording their version rather than recalculating historical releases.

Do not attempt to make Cycles and Three.js pixel-identical. Match camera framing, exposure, neutral material references and lighting intent; compare representative paint, carbon, rubber and metal patches in both. Only add export LOD/baking after measuring triangles, draw calls, GPU memory, download size, load time and frame-time distribution. If separate high/detail and delivery meshes are introduced, derive both from the same controls and maintain separate representation hashes plus a shared configuration ID. Prevent details disappearing from the website while looking good only in Blender.

Blender's subdivision documentation supports low-vertex control meshes with deliberate creases; its glTF guidance specifies texture-backed tangent-space normal export. These support this proposal, but do not establish F1 dimensions. [S1–S3]

## Build stages and execution improvements

Retain one worker/job ownership model initially. Implement sequential checkpoints inside the job rather than creating more services:

- Resolve and freeze all inputs, software identity, device, seed, effective samples, adaptive threshold and denoiser availability.
- Build/export geometry and save a source scene; validate geometry/history before Cycles renders.
- Render all cheap previews and component close-ups before any 4K images. Surface a private draft review checkpoint. Make explicit whether the job is preview-only or final; partial output must never be marked ready.
- For final work, render four 4K views from the validated frozen scene. Record per-stage/per-view timing and memory, and keep hashes for successful checkpoints.
- Resume only when configuration/source/software/render-setting hashes match and job lease ownership is valid. Start with resume of verified rendered views, not general component caching. Keep the current annotation-only byte reuse.
- Run final artifact validation and existing four-view publication gate. Preserve historical artifacts and current pointers until replacement publication succeeds.

Reuse `--geometry-only`, `--preview-only`, `build_preview` and the neutral fixture. Any new checkpoint behavior must update task retries/leases, CLI/native adoption, manifests, schemas, preview API/UI status and tests together. Final render settings are distinct from authoring mesh detail. Capability checks must verify denoising actually works on the selected device; do not silently change platforms just to obtain better timings. [S4]

## Ordered delivery plan and acceptance

| Phase | Work and files affected | Exit condition |
|---|---|---|
| 0. Lock evidence and benchmark | Catalog/reference records, fixed cameras, render metadata, `render_wing_review.py` extension. Reverify dates and configuration identity; add diffuser photos or explicitly record missing coverage. | Comparable parent/pilot views and a repeatable time/memory/frame-time baseline; no claims of current race fitment without evidence. |
| 1. Construction separation | Extract diffuser function; distinguish control profiles from mesh resolution in `build_car.py` and catalog validation. | Unchanged baseline exports/hashes before topology changes; old specs remain supported. |
| 2. Front-wing pilot | Implement local section controls and multi-rail endplate/foot transitions; derive supports from surfaces. Start McLaren; use Racing Bulls to test whether the same mechanism expresses a genuinely different shape. | Reference-backed silhouette improvement, clear slots, seated hardware, stress-case passes, only declared components changed. |
| 3. Diffuser pilot | Add spanwise ramp controls, visible wall paths and shared floor interface for the team with the best underside/rear evidence. | Continuous visible floor junction, plausible observed outlet, no unsupported hidden detail, correct changed-component declarations. Missing evidence blocks accuracy claims, not the general construction prototype. |
| 4. Shading/delivery | Pilot UVs, normal/roughness maps, selective sharp edges; extend fingerprint coverage and browser comparisons. | No material loss on GLB export, acceptable seam behavior, no masked geometry defect, measured browser cost. |
| 5. Cheap-first worker | Early validation, preview-first order, frozen settings and safe resume; keep current services. | A deliberately invalid model fails before final rendering; an interrupted view resumes safely; partial builds cannot publish. |
| 6. Full acceptance | Three paired baseline/revised benchmark runs on identical hardware/settings policy, four preview + four 4K outputs, complete-car and close-up review, API/browser and hosted CI. | Approved image quality, complete immutable artifacts, measured runtime and browser budgets, then explicit release publication and Pages snapshot update. |
| 7. Expand to other teams | Author evidence-backed profiles using the proven controls, not copied pilot geometry under different paint. | Per-team references, uncertainty notes, review and all-grid regression checks. |

Prioritize phases 0–3 before broad material work. Early validation from phase 5 can be pulled forward once interface changes are clear. Do not increase render sample ceilings again while evaluating structural changes.

## Measurements and regression gates

- Use the old 2026.6/128-sample full worker workload versus the final candidate at its chosen release settings to assess the user's original approximately 20–30% total-time budget. Separately compare 2026.9 and the next generator at equal settings to isolate structural cost. Do not combine unrelated historical timings or pretend sample-count changes equal runtime changes.
- Run sequentially, record warm/cold conditions and median plus range of at least three paired runs, with four 1080p previews and four 4K views. Include geometry/export/bake/render/validation in the total. A faster build meeting quality is acceptable; do not waste time to reach a lower bound.
- Proposed performance gate: at most 30% median full-build overhead versus the agreed original baseline, no more than 10% median browser frame-time regression at matched camera/device/resolution, and report p95 plus peak memory. Treat these as proposed engineering limits, not existing measured results. Record absolute results on a second device before claiming broad performance.
- Keep all eleven component IDs, embedded assets, bounds/orientation/grounded tyres and deterministic component histories. Add negative tests for flattened endplates, disconnected supports/strakes, closed slots, bad floor seams and omitted exported material data. Test parameter extremes, not only defaults.
- For shape accuracy, align reference camera/perspective using trustworthy landmarks; compare visible silhouette and feature placement in several views. Do not prescribe a fake universal millimetre accuracy from an uncalibrated photo. Set image-specific tolerances tied to evidence resolution; label occluded areas unverified.
- Run backend and archive tests, frontend typecheck/lint/build, live-app and Pages browser suites, full-grid Blender checks and hosted CI after implementation. Tests do not substitute for visual approval. A new public snapshot requires final models, four-view review and release validation, not just a successful code deploy.

## Geometry improvement backlog — 2026-11-10

This proposed backlog extends the construction plan to whole-car shape. It is based on generator inspection, not a completed visual comparison or factory measurements. Complete the wing/diffuser pilots first; insert body-shape passes before broad material work. Review each pass independently.

### Authoring and compatibility

- Establish wheel centers, ground plane, axle spacing, nose tip, cockpit aperture and wing envelopes as reference landmarks. Preserve `V`: authoring X is lateral, Y is height, Z is longitudinal. Align photographs of the same configuration before changing proportions.
- Build silhouette curves → cross-sections at curvature changes → surface patches → thickness/junctions → visible hardware. Require tangent continuity on smooth panels, sharp trailing edges and open gaps between separate laminates.
- Put detailed controls in optional, versioned team profiles initially. `validate_parameters` requires exactly the catalog's scalar keys; new required API parameters would invalidate older revisions. Preserve those keys and defaults. Validate profiles separately for finite coordinates, ordered stations, compatible sections, positive thickness and non-crossing boundaries.
- Freeze effective profiles and their hashes. Profile-only geometry edits still require declared component revisions and generator identity; catalog edits must not silently redefine old specs. Keep frozen releases immutable.
- Add local control loops before extra samples. Increase tessellation only when fixed close-ups reveal faceting. These are authoring controls, not internal rods to display in the finished model.

### Pass A — front and rear wing character

**Front:** implement the earlier local camber/twist and endplate shoulder controls. Give flap roots and outboard terminations explicit boundary paths so changing sweep does not simply stretch the same tip. Derive nose/pylon contacts from shared surfaces. Concentrate geometry at tip curvature, thin slot exits and endplate/foot junctions.

**Rear:** extend `build_rear_wing` with independent central spoon depth, shoulder transition, outboard rise and flap trailing-edge paths. Where references justify it, replace two-rail endplates with shoulder patches controlling upper tip and lower skirt. Derive pylon/separator endpoints from evaluated surfaces. Model visible hinge/fairing contours without inventing internal actuators or assuming a universal element count.

**Accept when:** aligned front/rear/oblique silhouettes improve; smooth junctions have no artificial highlight dents; slots remain open in GLB; supports stay attached under chord/camber changes. Pilot McLaren and Racing Bulls, then author other teams from their own evidence. Review the observed wing pose; animation is outside this pass.

### Pass B — connected floor and diffuser

The floor already samples 81 by 25 vertices, but uses one cubic cross-car height formula. Add inner, shoulder and outer-edge height rails at selected longitudinal stations; keep the existing outline as fallback. Derive edge-slot boundaries and bridge endpoints from these surfaces instead of fixed offsets. Add cuts/fences only where dated references establish them.

Connect these rails to the earlier diffuser design: variable width, cross-car outlet heights and swept visible dividers. Share interface samples to prevent cracks or doubled surfaces while retaining assembly ownership.

**Accept when:** low side/rear views show a continuous transition, slots remain open, and dividers meet the ramp without blocking channels. Declare floor and diffuser revisions together when their interface moves. Hidden underside accuracy remains unresolved.

### Pass C — sidepod shoulder, undercut and rear taper

`pod_surface` already forms an undercut, but derives nine contour points per station from fixed proportions; one channel-depth value drives roof depression. Add optional shoulder, maximum-width, undercut and lower-return landmarks. Control roof-channel position, width and depth independently only where evidence supports it. Preserve the nine-point fallback.

Place sections at inlet, maximum shoulder, deepest visible undercut, start of rear taper and exit. Allow shoulder and belly to narrow at different rates. Derive inlet rim and duct entrance from the shell boundary, preserving `front_boundary` or its shared-boundary contract. Use a shaped lip where a constant-radius tube cannot match the contour. Internal duct termination remains an approximate enclosure.

**Accept when:** side/front-oblique views capture inlet height, overhang and rear taper independently; the inlet stays open, rim seated and roof free of unintended pinches. Select the pilot by matched reference coverage.

### Pass D — nose, cockpit and engine-cover silhouette

`loft` uses a shared superellipse family. Add explicit section outlines only where it cannot independently represent a flatter top, rounded shoulder and tucked lower edge. Preserve ring ordering/outward normals; retain the helper for simpler surfaces.

- **Nose:** separate dorsal/lower profiles, shoulder width and tip curvature. Derive wing-pylon contacts from shared boundaries; fix the chassis transition before panel lines.
- **Cockpit:** refine the working aperture rim and sill against references, keeping the inner tub below the opening. Retain the Boolean unless a required contour makes it unstable; then evaluate a direct rim patch.
- **Engine cover:** control airbox-to-spine shoulder and rear taper independently. Replace visible accidental overlaps between `engine_body`, `upper_spine` and `airbox_outer_cowl` with shared boundary patches where a continuous skin is supported. Preserve real panel seams.
- **Openings:** replace the exhaust-end proxy with a short hollow rim/recess where visible. Replace illustrative cooling-relief tubes with shallow openings only when references establish their position/count.

**Accept when:** side/top silhouettes improve without artificial ridges under grazing light; cockpit/airbox remain open. Nose and engine-cover changes can move surface-derived suspension mounts and projected ribbons: inspect hashes and declare dependent component revisions rather than requiring only the edited body assembly to change.

### Pass E — visible mechanical interfaces

After primary surfaces pass review, refine suspension/halo contours. Use reference-backed external landmarks for wishbones and push/pull/steering members, retaining body-surface seating. Add local fairing taper and junction transitions. Replace generic brake-duct boxes with bounded inlet shells where visible evidence supports them; do not infer factory hardpoints or kinematics.

Allow halo fairing cross-section and attachment feet to vary instead of using only constant circular tubes. Keep existing open wheel barrels/rotors; refine tyre shoulders and spoke sections only where close-ups reveal a mismatch. Extra bolts and rotor marks are lower priority.

**Accept when:** interfaces remain seated and wheel/duct/suspension clearance checks pass in the static pose. Steering/travel behavior requires separate implementation and validation.

### Implementation scope and verification

Start in `modeling/build_car.py` and `modeling/catalog.json`. Extend profile validation through `backend/app/services/catalog.py` and the build boundary. Update `backend/app/geometry_check.py`, affected `backend/app/tests`, `scripts/render_wing_review.py` and dated `data/references` records. Extend the existing review fixture rather than adding a render pipeline. Check release/history services for coupled components; verify exports in `CarViewer.tsx` and `scripts/benchmark_viewer.cjs`. Change the viewer only for a demonstrated defect.

For every pass, capture matching-camera parent/candidate views in neutral clay and production materials, in Blender and the browser, with full-car context and relevant close-ups. Record silhouette/landmark errors, continuity defects and attachment/gap failures separately as improved, unchanged, worse or unverified. More vertices or different hashes do not prove realism; missing references limit accuracy claims.

Keep lighting, seed, resolution and samples fixed while comparing shape. Measure each pass and the combined candidate against the original total-build budget above; do not grant another 30% allowance per pass. Reduce invisible tessellation and deferred micro-detail before compromising primary surfaces. No implementation, new geometry render or timing measurement was performed when this backlog was written.

## What is deliberately excluded

No blanket subdivision increase, speculative internal aero, wholesale remeshing, photogrammetry from unrelated viewpoints, new rendering framework, additional Docker services, or GPU/cloud migration without a measured need. No new sponsor artwork or unlicensed scans. No automatic publication from this reference. Full 4K quality and the original combined runtime target remain unvalidated for current 2026.9 drafts.

## Primary sources consulted and applicability

S1. Blender 4.5 LTS, Subdivision Surface: https://docs.blender.org/manual/en/4.5/modeling/modifiers/generate/subdivision_surface.html — control mesh, smoothing and edge creases. Design guidance; prototype on the pinned Blender 4.3.2 runtime before adopting API details.

S2. Blender glTF exporter manual (4.0): https://docs.blender.org/manual/id/4.0/addons/import_export/scene_gltf2.html — texture-backed normal/roughness/occlusion export. Retrieved text is English despite the locale URL. Verify actual 4.3 exporter output.

S3. Blender 4.4, Render Baking: https://docs.blender.org/manual/en/4.4/render/cycles/baking.html — selected-to-active surface baking and UV margins; candidate for fine detail, not a substitute for silhouette geometry.

S4. Blender Cycles sampling: https://docs.blender.org/manual/de/3.0/render/cycles/render_settings/sampling.html — adaptive sampling uses noise thresholds, so maximum samples do not imply linear runtime. Retrieved text covers the general mechanism; settings must be verified on 4.3.2.

S5. OpenAI, custom instructions: https://learn.chatgpt.com/docs/agent-configuration/agents-md — repository `AGENTS.md` provides project instructions. This reference is stored only in the repository at the user's request; it does not modify global Codex guidance.

Direct retrieval of several Blender 4.3/latest manual URLs failed in the web tool. The accessible official indexed versions above provide conceptual guidance, not proof of runtime feature compatibility. The proposed F1 construction structure is an engineering recommendation derived from repository inspection; Blender documentation does not validate the car-specific geometry.
<!-- END F1 BLENDER STRUCTURE REFERENCE -->
