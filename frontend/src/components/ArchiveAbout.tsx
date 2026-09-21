import Link from "next/link";

export default function ArchiveAbout() {
  return (
    <article className="archive-about">
      <p className="eyebrow">FORM & FLOW / THE ARCHIVE</p>
      <h1>Every shape has a source.</h1>
      <p className="lede">
        Explore original 2026 constructor exterior reconstructions, grounded in
        dated public references.
      </p>
      <h2>From observation to release</h2>
      <p>
        Team photography, FIA submissions, and technical reporting establish
        visible changes. Each reconstruction is inspected from front, side,
        rear, and perspective views against the available references before
        publication. Hidden geometry and dimensions without a source remain
        estimates.
      </p>
      <p>
        A reported upgrade can appear as an annotation when the evidence cannot
        support a new shape. Release dates describe the observed configuration;
        the evidence cutoff records what was available to its reviewer. Launch
        references do not establish the latest race specification.
      </p>
      <h2>An archive you can inspect</h2>
      <p>
        Select an assembly to see its evidence and uncertainty. When a team has
        multiple releases, compare their geometry with synchronized cameras and
        download the studio renders. Earlier releases remain available after a
        revision or reversion.
      </p>
      <h2>How updates reach this site</h2>
      <p>
        This site displays a snapshot of reviewed releases. Collection, Blender
        rendering, and the maintainer’s review studio run locally. New work
        reaches the archive after review and a successful deployment; this site
        does not collect articles or render cars in the background.
      </p>
      <p>
        Built with original geometry and materials. This independent project is
        not affiliated with Formula 1, Ferrari, Mercedes, or the FIA.
      </p>
      <div className="toolbar-controls">
        <Link className="button" href="/models">
          Explore the archive →
        </Link>
        <a
          className="text-link"
          href="https://github.com/prayag2301/f1-engineering-dashboard"
        >
          Source and local setup ↗
        </a>
      </div>
    </article>
  );
}
