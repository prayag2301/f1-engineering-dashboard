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
