# Wing and floor reconstruction — evidence reviewed 14 September 2026

Generator **2026.4** replaces the shared three-strip wings and flat floor with independently authored Ferrari and Mercedes surfaces. This is an exterior approximation, not photogrammetry or team CAD. The numerical stations describe the model; they are not measured dimensions of a race car.

## Configuration and dates

The draft corrections retain the January launch observation dates. The rest of each car is the previously reviewed launch reconstruction. Applying September aero to that body and labeling the result a complete Madrid car would mix configurations without evidence. Recent submissions are therefore separate **draft, annotation-only candidates**, pending review and more photographic coverage. Publication still requires the existing four-view visual review.

The latest official material examined was Mercedes' Madrid gallery (updated through 13 September), Ferrari's 1 September Monza livery presentation, and FIA submissions for Monza (4 September) and Madrid (11 September). Ferrari's Madrid page returned an access error. The accessible September Ferrari presentation does not prove which parts were fitted during the race. FIA location diagrams repeat a generic car; **do not trace those diagrams as team geometry**.

## Visual references and reconstruction decisions

| Assembly | Ferrari SF-26 | Mercedes W17 | Limits |
|---|---|---|---|
| Front wing | Broader swept upper-flap outline; raised middle span and dropped outer junction; curved endplate and thin outboard foot. | Narrower upper flaps; outer mainplane trough and rolled foot; a different scalloped endplate rail. | Front, top and three-quarter views constrain visible outlines. Perspective, airfoil sections, slot clearance and brackets remain estimates. |
| Rear wing | Deeper spoon-shaped mainplane and more pronounced spanwise rise. | Shallower mainplane bowl and more uniform upper-flap height. | Closed element skins replace identical stacked strips. Thin pylons and curved lower endplates approximate visible supports; mechanisms are unresolved. |
| Floor | Swept board and lower turning surface; later and shallower edge-lip rise. | Different board sweep, raised forward shoulder and edge-height progression. | Reconstruct only the visible upper perimeter. Hidden tunnels, underside contour, exact small-fence layout and aerodynamic performance are not established. |

January primary references:

- [Ferrari official launch images, published by Formula 1, 23 January](https://www.formula1.com/en/latest/article/gallery-check-out-every-angle-of-ferraris-2026-f1-car.7HdOPtJJwN5VHJ8XAWVtuS): front `F678_still_f03`, rear three-quarter `f15`, overhead `f08`.
- [Mercedes W17 presentation, 22 January](https://www.mercedesamgf1.com/news/mercedes-amg-f1-2026-challenger-w17-revealed): three-quarter `GR_6`; overhead `KA 12` and side `KA 10` in the official presentation gallery.

September cross-checks:

- [Mercedes Madrid official gallery](https://www.mercedesamgf1.com/news/in-pictures-the-best-images-from-madrid-2026): `M627356` shows the front wing and visible floor in three-quarter view; `M629056` shows the front wing nearly head-on. The gallery's initial publication date is 10 September; later images were added through 13 September. Upload time is not treated as the exposure time. These views corroborate the general construction but do not prove January/September part identity or provide the hidden floor shape.
- [Ferrari Monza livery presentation, 1 September](https://www.formula1.com/en/latest/article/gallery-ferrari-reveal-schumacher-inspired-livery-for-home-grand-prix-at-monza.5burkVG8etBZzPdZrIN7bX): `ferrari-monza-livery-2026-3` is a close front-wing view, `-4` an elevated front view, `-2` a side view and `-1` a rear-quarter view. Presentation imagery is not proof of the raced Monza aero configuration.

## Recent change evidence

| Source | Team / assembly | What it establishes | Representation |
|---|---|---|---|
| [FIA Italian GP submissions](https://www.fia.com/system/files/decision-document/2026_italian_grand_prix_-_car_presentation_submissions.pdf), document 10, 4 September, page 8 | Ferrari / floor board | A revised front floor-board arrangement using a single vertical element. | Annotation-only. The location diagram supplies no team-specific dimensions or detailed contour. Do not infer the whole floor or continued use at Madrid. |
| Same document, page 4 | Mercedes / rear wing | Removal of winglet devices for Monza's drag range. | Annotation-only; circuit-specific, not a permanent season-wide deletion. |
| [FIA Spanish GP submissions](https://www.fia.com/system/files/decision-document/2026_spanish_grand_prix_-_car_presentation_submissions.pdf), document 11, 11 September, page 4 | Mercedes / rear wing | Reduced span of the central winglet above the rear-wing flap for Madrid. | Annotation-only. The precise earlier/later spans are not supplied. |
| Same document, page 8 | Ferrari | Listed change concerns a rear-suspension fairing. | No new Ferrari wing/floor claim is made from this submission. Absence from this list is not proof of an unchanged car. |

See [the machine-readable evidence record](../data/references/aero-2026-09-14.json) for passages, page numbers, dates and review status. External photographs and PDFs are reference-only and are not redistributed with the viewer or GLB.

## Geometry and review

`modeling/build_car.py` contains editable stations for each element, shape-preserving cubic interpolation, closed airfoil skins, and thin shells between curved rails. No new paid assets or textures are used. The existing carbon material remains embedded in the GLB. Nose, body, wheels, suspension, halo and diffuser geometry remain byte-identical at the component-hash level to the reviewed parent.

Inspect **Front-wing contours**, **Floor edge & boards** and **Rear-wing profiles**, with **Compare teams** and **Neutral surfaces** enabled. The private review screen can also compare drafts. Check complete-car views as well as isolated components: isolation can hide an attachment or clearance problem. Neither numerical validation nor visibly different geometry substitutes for the maintainer's reference comparison before publication.

While a build is rendering, the authenticated review screen can inspect its validated GLB and completed previews. Preview URLs identify the current job and attempt, use private/no-store caching, and stop working when that attempt is superseded. This does not change the stored release manifest or its `building` status. The public archive cannot see these assets; approval and publication remain unavailable until all four previews and four 4K renders pass the existing artifact gate.
