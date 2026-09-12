# Editable exterior reconstruction

`build_car.py` runs in Blender 4.3.2 from Debian trixie on ARM64 or AMD64. It builds an original car scene from explicit component parameters. The browser GLB and all studio views come from that same scene.

## Coordinates and ownership

Builder coordinates and GLB exports use metres, X lateral, Y up, and nose toward −Z. The wheelbase is 3.4 m. Blender's native Z-up coordinates are converted explicitly on construction and restored by the glTF exporter. Every exported object has a stable `component` extra and an origin at the catalog's component-local anchor.

Eleven assemblies are exported: chassis, nose, front wing, sidepods, engine cover, floor, diffuser, rear wing, suspension, wheels, and halo. The ground, camera, and lights exist only in the editable scene. Modifying one assembly must preserve all other assembly mesh hashes. The geometry smoke test verifies this with a front-wing revision.

Curved body sections use superellipse lofts and subdivision; the cockpit is a Boolean opening; halo and duct lips use Bézier curves; wings use closed airfoil sections; tyres have rounded revolved profiles. Sidepods sweep inward toward the rear engine body rather than scaling around the world origin.

## References and uncertainty

`catalog.json` contains dated official launch galleries, event names, reference-image URLs, team livery notes, and initial parameters. Each baseline component revision records its source and the remaining uncertainty. These are authored exterior estimates, not measured factory surfaces.

Ferrari follows the SF-26 launch's red nose/sidepods and white upper bodywork, with a triangular airbox outline. Mercedes uses silver forward paint, exposed dark bodywork, turquoise lines, a squarer airbox, and different nose, inlet, floor, and wing parameters. Wheel graphics and sponsor logos are omitted.

The source gallery must be checked in **front, side, rear, and three-quarter** views before accepting a baseline. The included image links are starting references, not a completed visual approval. Where a gallery does not establish a surface, document that uncertainty rather than certifying it.

## Local editing

Start with a downloaded `source.blend` and its matching `build_car.py`, `catalog.json`, and `spec.json`. To reproduce a draft inside the worker:

```sh
blender --background --python-exit-code 1 --python build_car.py -- \
  --input spec.json --output output --samples 128
```

`--geometry-only` skips PNGs. `--preview-only` makes four 1080p previews. A complete job additionally makes four 4K PNGs and stores SHA-256 checksums for all outputs.

Before the first publication, edit the baseline parameters in `catalog.json` and the relevant assembly in `build_car.py`, rebuild the API and worker images, then choose **Build revised baseline** in the review studio. This creates a new draft and retains the previous renders for comparison.

For later parameter-supported changes, use the maintainer release form. More substantial topology changes require editing the relevant builder assembly, bumping the generator version in both the catalog and geometry metadata, adding an explicit reviewed revision, and rerunning the geometry smoke test. The worker rejects changed geometry in any assembly the release declares unchanged.

An earlier published configuration can be restored without deleting history. Annotation-only releases copy the parent's exact scene, GLB, and render bytes and retain their own evidence/spec snapshot.

## Original assets

Carbon twill is an original packed UV texture generated mathematically. Paint, rubber, intake darkness, and magnesium use physically based materials. Studio reflection cards and lights are original; no external HDRI download is required. No licensed team CAD, commercial asset, game model, or scraped sponsor texture is included.

The FIA document URLs constrain the reviewed dimensions only. Team photographs remain external reference media under their owners' rights and are not part of exported scenes.
