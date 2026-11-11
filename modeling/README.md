# Editable exterior reconstruction

`build_car.py` runs in Blender 4.3.2 from Debian trixie on ARM64 or AMD64. It builds an original car scene from explicit component parameters. The browser GLB and all studio views come from that same scene.

## Coordinates and ownership

Builder coordinates and GLB exports use metres, X lateral, Y up, and nose toward −Z. The wheelbase is 3.4 m. Blender's native Z-up coordinates are converted explicitly on construction and restored by the glTF exporter. Every exported object has a stable `component` extra and an origin at the catalog's component-local anchor.

Eleven assemblies are exported: chassis, nose, front wing, sidepods, engine cover, floor, diffuser, rear wing, suspension, wheels, and halo. The ground, camera, and lights exist only in the editable scene. Modifying one assembly must preserve all other assembly mesh hashes. The geometry smoke test verifies this with a front-wing revision.

Curved body sections use superellipse lofts and subdivision; the cockpit is a Boolean opening; halo and duct lips use Bézier curves; wings use closed airfoil sections; tyres have rounded revolved profiles. Sidepods sweep inward toward the rear engine body rather than scaling around the world origin.

## References and uncertainty

`catalog.json` contains dated official launch galleries, event names, reference-image URLs, team livery notes, and initial parameters. Each baseline component revision records its source and the remaining uncertainty. These are authored exterior estimates, not measured factory surfaces.

Ferrari follows the SF-26 launch's red nose/sidepods and white upper bodywork, with a triangular airbox outline. Mercedes uses silver forward paint, exposed dark bodywork, turquoise lines, a rounded airbox with a divider, and different nose, inlet, floor, and wing parameters. Wheel graphics and sponsor logos are omitted.

Generator `2026.2` revises four assemblies against the same launch galleries: chassis, nose, sidepods and engine cover. Sidepods now use asymmetric section stations with separate shoulders and undercuts. Ferrari has a broad forward opening and a fuller shoulder; Mercedes has a shallow high slot and an earlier descending ramp. Inlet rims follow the evaluated body boundary to keep the openings connected to the surrounding surfaces. Airboxes have continuous outer fairings and recessed ducts, with separate team outlines and a Mercedes divider. Engine shoulders, spine and fin use separate station layouts. A dark inner cockpit tub corrects the previously obscured seat. Exact station dimensions are authored estimates, and the Ferrari cooling-relief count is illustrative. The seven other assemblies retain their prior construction.

The geometry check compares material-independent shape hashes for those three assemblies. This proves that the team differences are in the mesh, but does not replace reference review or certify factory dimensions. Suspension remains a shared estimated assembly; this revision does not assert that the real teams use identical suspension geometry.

Generator `2026.3` corrects the Mercedes rear profile after comparison with the official side and overhead launch renders: a relatively flat deck, shallow upper channels, rear upsweep and a higher dorsal fin. See the [January 22 launch gallery](https://www.formula1.com/en/latest/article/gallery-check-out-every-angle-of-mercedes-new-livery-for-2026.70sm6Znl139u64MesOt5Vf) and [F1's contemporary technical analysis](https://www.formula1.com/en/latest/article/tech-analysis-have-mercedes-pioneered-a-left-field-solution-with-their-new.6fpytwTL29cap2mrQuAEdc). These are presentation-render features; correspondence with the actual racing car is unconfirmed. Ferrari's `2026.2` geometry is retained. The earlier, unbuilt Mercedes draft is preserved as superseded, not published.

The source gallery must be checked in **front, side, rear, and three-quarter** views before accepting a baseline. The included image links are starting references, not a completed visual approval. Where a gallery does not establish a surface, document that uncertainty rather than certifying it.

## Local editing

Start with a downloaded `source.blend` and its matching `build_car.py`, `catalog.json`, and `spec.json`. To reproduce a draft inside the worker:

```sh
blender --background --python-exit-code 1 --python build_car.py -- \
  --input spec.json --output output --samples 128
```

`--geometry-only` skips PNGs. `--preview-only` makes four 1080p previews. A complete job additionally makes four 4K PNGs and stores SHA-256 checksums for all outputs.

Docker jobs always default to CPU. A native macOS Blender installation can use `--device METAL` for local review renders; it fails explicitly if no Metal device is available. This option does not change model geometry or enable GPU passthrough in Docker. Final publication still runs the normal artifact and historical-component checks in the release workflow.

Before the first publication, edit the baseline parameters in `catalog.json` and the relevant assembly in `build_car.py`, rebuild the API and worker images, then choose **Build revised baseline** in the review studio. This creates a new draft and retains the previous renders for comparison.

For later parameter-supported changes, use the maintainer release form. More substantial topology changes require editing the relevant builder assembly, bumping the generator version in both the catalog and geometry metadata, adding an explicit reviewed revision, and rerunning the geometry smoke test. The worker rejects changed geometry in any assembly the release declares unchanged.

An earlier published configuration can be restored without deleting history. Annotation-only releases copy the parent's exact scene, GLB, and render bytes and retain their own evidence/spec snapshot.

To improve a published model of the *same* observed car, choose **Improve an existing reconstruction** in the release form. The API requires the original observed date and event, explicit component revisions, references, and correction notes. It rejects upgrade candidates in this mode. New files remain drafts until all four views are reviewed and publication is explicitly requested. Historical originals and current public assets are retained. Use the component notes in `catalog.json` as starting descriptions of these corrections.

The viewer's **Compare teams** mode synchronizes cameras across two independently dated releases. **Show neutral surfaces** removes livery ribbons and uses a shared matte finish; **Isolate component** and the three close-up shortcuts expose details. Each comparison pane links its own frozen component evidence. These controls also work with the previously published geometry; deploying the viewer does not publish pending reconstruction corrections.

For the catalog's prepared launch corrections, after rebuilding the API/worker images:

```sh
docker compose exec api python -m app.cli correct-launch PUBLISHED_LAUNCH_VERSION_UUID
```

This creates and queues an authenticated local draft with four explicit revisions and the original references. It rejects later race configurations and releases already using the current generator. It neither records a visual approval nor publishes. Review the output at `http://127.0.0.1:3000/review` before publication and a new Pages export.

## Original assets

Carbon twill is an original packed UV texture generated mathematically. Paint, rubber, intake darkness, and magnesium use physically based materials. Studio reflection cards and lights are original; no external HDRI download is required. No licensed team CAD, commercial asset, game model, or scraped sponsor texture is included.

The FIA document URLs constrain the reviewed dimensions only. Team photographs remain external reference media under their owners' rights and are not part of exported scenes.

## Full constructor grid (2026.6)

The catalog now also includes McLaren MCL40, Red Bull RB22, Aston Martin AMR26,
Alpine A526, Williams FW48, Haas VF-26, Racing Bulls VCARB 03, Audi R26 and
Cadillac MAC-26. These baselines are dated to Madrid Friday practice on
11 September, not backdated to launch. The reference audit is in
`data/references/grid-2026-09-21.json`: selected image URLs, file hashes,
observations and unresolved areas. Incorrectly labelled/irrelevant gallery
images were excluded after visual inspection. Photographs remain external
references and are not embedded in exported models.

Each new constructor has explicit sidepod section stations, nose dimensions,
airbox outline, fin height, wing parameters and livery colours. Material-free
shape fingerprints distinguish the models. Shared construction of estimated
parts is disclosed; these are original exterior estimates, not factory CAD or
validated aerodynamic simulations. Williams uses the photographed Madrid
white livery. Cadillac has separate black/white body sides; sponsor graphics
are omitted throughout. Ferrari and Mercedes retain their existing geometry.

For a native build (including four 1080p previews and four 4K renders):

```sh
python3 scripts/build_grid.py --teams mclaren audi cadillac \
  --output data/releases/my-grid-build --blender /path/to/blender \
  --device METAL --samples 64
```

Use `--device CPU` on other platforms. Each output directory freezes its
builder, catalog, regulations and spec; an existing directory is never
replaced. `--geometry-only` is useful for smoke checks. Run one job by default;
`--jobs 2` is optional when memory and GPU capacity permit.

A validated native build can be attached to its unfinished draft with
`python -m app.cli adopt-native VERSION_UUID /mounted/build/directory` inside
the API container. The importer checks team, parameters, frozen generator,
component history and every artifact before marking it ready. It refuses
published/ready versions and builds with an active worker. Four-view review
and normal publication still follow.

See [weekly intake](../docs/weekly-updates.md) for local scheduling and the
portable GitHub Actions report.

## Construction detail pass (2026.7)

New builds include open rim barrels, recessed brake rotors and calipers, rotor
mounting hardware and valve stems. Cockpits gain a display, grips, buttons,
shoulder harnesses and a buckle; exhaust outlets gain a dark recessed aperture.
These are generic estimated construction details, not verified team internals
or evidence of a race upgrade. Rotor ventilation marks are surface details,
not simulated cooling passages. They are actual GLB meshes with the existing
assembly IDs, so the browser receives the same detail as the studio scene.
Vent marks are batched per wheel to limit added browser draw calls.

Only `chassis`, `engine_cover` and `wheels` change in this pass. A reconstruction
draft must declare all three revisions; the eight other assemblies retain their
existing hashes. Earlier scenes and published snapshots are not regenerated.
The all-grid geometry check verifies exported detail, watertight open sleeves,
component identity and the existing surface/contact checks.

The default sample ceiling increases by 25%: native/builder jobs use 80 instead
of 64, and Docker worker jobs use 160 instead of 128. Existing explicit sample
overrides remain effective. Adaptive sampling makes actual time depend on the
view and hardware; a sample increase is not itself a measured time increase.
Rebuild the API and worker images together before creating reconstruction drafts.

On 7 November the sequential Docker CPU pilot measured 151.85 seconds for the
unchanged McLaren at 32 samples, 161.77 seconds for the detail pass at the same
32 samples (+6.54%), and 194.25 seconds with detail and 40 samples (+27.93%
against baseline). Each run built geometry, GLB, the editable scene and four
1080p previews. This is one run per setting, not a full 4K timing guarantee.
The resulting GLB has 226,384 triangles (+7.83%), 244 mesh nodes (from 191)
and 6,013,036 bytes (+10.06%). The existing website viewer loaded the new GLB
and measured 59.85 FPS (479 frames over 8.0031 seconds) at 1920×1080 on Apple M1
Metal. This single local run may overlap Docker geometry checks and is not a
cross-device performance guarantee.
See [the benchmark record](../data/references/detail-benchmark-2026-11-07.json).
The review artifacts are in `data/releases/detail-2026-7/quality/`; they are
unpublished 40-sample previews, not completed 160-sample publication renders.

### Repeatable wing realism review (2026.9)

The McLaren and Racing Bulls pilot corrections add curved upper endplate rims,
crowned front footplates, revised lower rear-endplate stations, and rear pylon
mounting shoes/fasteners. These remain exterior estimates from the saved
September photographs; no observation dates or published pointers change.

Use the same fixture for both frozen scenes:

```sh
blender --background --python-exit-code 1 --python scripts/render_wing_review.py -- --scene PATH/source.blend --output NEW_REVIEW_DIRECTORY
```

The fixture emits neutral front/rear wing PNGs at fixed 1280×720 cameras and
48 samples. It refuses to overwrite reviewed images and does not save changes
to the input scene. Full render sampling is unchanged. Matching images support
visual comparison; they do not establish full 4K quality or the combined runtime
budget. Pilot artifacts are in `data/releases/realism-2026-9/`.

### Wing shape controls (2026.10)

The first geometry-plan pass adds an optional eighth airfoil-station column:
the chord fraction of maximum camber (0.25–0.75). Seven-column profiles retain
the original centered camber. A smooth remapping moves that maximum while
preserving the leading/trailing positions. Exported skins and surface-mounted
supports evaluate the same curve; existing rise/sweep controls still set twist
and planform.

`endplate_shoulder` supplies a third rail at the same stations as `endplate`.
Its points describe the surface midpoint between the boundary rails, before
the existing upper-edge roll. This first version permits bounded lateral
shaping; height and longitudinal position remain the boundary midpoint to
avoid folded patches. Both boundaries stay fixed. McLaren and Racing Bulls
use small estimated shoulder offsets and spanwise camber-peak changes. These
are reconstruction candidates, not newly measured dimensions or race upgrades.

`wing_profiles.py` validates these controls before scene construction and when
the backend loads the catalog. Worker/native builds freeze this helper beside
the builder and catalog; adoption verifies its source and release validation
requires its checksum for the new profile schema. Legacy annotation-only
releases retain their original source set. Dockerfiles already copy the entire
modeling directory; rebuild API and worker images together before using the
new generator. Published snapshots are unchanged.

Only the two wing assemblies should change for the pilots. Sampling ceilings
are unchanged; full-build timing and final photographic accuracy still require
the plan's separate acceptance gates. Local comparison artifacts belong under
`data/releases/shape-2026-10/`.

The [validation record](../data/references/shape-validation-2026-10.json) records
149 backend tests, 14 archive tests, 14 Blender grid/variation cases and both
browser smoke checks. Matched pilot exports change only the two wings, with
approximately 2.1% more triangles. Neutral before/after fixtures show subtle
contour changes; they do not establish photographic accuracy or a full-build
performance result.

For private Studio inspection before final renders exist, call
`adopt_build(db, version_id, directory, inspection_only=True)` for a draft whose
specification and declared component revisions match the frozen build. This
checks the source, catalog, geometry and component history, then stores the
assets under `.inspections/<version_id>` in the release volume. The version
remains a draft: authenticated reviewers can rotate, isolate and compare its
model, while final review and publication stay unavailable. A later full build
uses the normal release directory and artifact gates. The checked import stays
available while that build is queued or exporting geometry; the active build's
validated preview takes precedence once available. A completed release uses
its own assets without overwriting the inspection files.

The local McLaren and Racing Bulls imports are recorded in
[Studio inspection verification](../data/references/studio-inspection-2026-10.json).
They retain the existing observation dates and published pointers. Their
revisions also declare earlier reconstruction changes relative to the public
2026.6 parents; the 2026.9-to-2026.10 comparison above changes only the wings.
