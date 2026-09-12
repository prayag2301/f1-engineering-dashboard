# GitHub Pages deployment

The replacement application lives on `codex/github-pages-release`. The existing
site at https://prayag2301.github.io/f1-engineering-dashboard/ was deployed from
`demo/static`. It stays live while the replacement is built and reviewed.

## Runtime and local workflow

Pages serves the exported Next.js viewer, public evidence metadata, GLBs, and
PNGs. Navigation, direct team links, comparison, and downloads work under the
repository subpath, without an API or database. The review route on Pages
explains the archive and never requests credentials.

Docker runs collection, Blender, and the authenticated review studio locally.
Monday collection does not automatically publish or deploy. After a reviewed
release or rollback, export a new snapshot to update the public site.

## Preview a clean checkout

Requires Node 20 and Python 3.11 or later; Docker is not needed:

```sh
npm --prefix frontend ci
npm run build:pages
npm run preview:pages
```

Open http://127.0.0.1:4173/f1-engineering-dashboard/. The preview serves exported
files with real subpath redirects and 404s. It does not emulate an API.

`data/pages/snapshot.json` pins a public GitHub Release tag and archive SHA-256.
An empty descriptor builds an honest empty archive that CI tests but refuses
to deploy over the current site. Drafts and synthetic cars never enter the
bundle. A populated descriptor downloads and verifies the exact pinned snapshot.

Preview a local bundle before uploading it:

```sh
PAGES_ARCHIVE="$PWD/data/pages-export/2026-09-14/pages-archive.tar.gz" npm run build:pages
npm run test:pages
```

`PAGES_ARCHIVE` only overrides local builds; CI uses the committed pin. For a
custom domain or an owner site, build with `NEXT_PUBLIC_BASE_PATH=''` and preview
with `--base-path=''`. Project sites use the repository name as their base path.

## Export an approved snapshot

Publish both Ferrari and Mercedes baselines in the local studio at
http://127.0.0.1:3000/review after comparing all four views to references.
Build completion alone does not approve a model. Then export:

```sh
python3 scripts/pages.py export \
  --api http://127.0.0.1:3000 \
  --output data/pages-export/2026-09-14/pages-archive.tar.gz
```

Choose a fresh dated directory each time. The exporter never overwrites an
existing bundle. It uses unauthenticated public endpoints and rejects missing
baselines, unreviewed releases, incomplete history, broken pointers, unexpected
filenames, invalid GLB/PNG headers, and corrupt bytes.

The bundle contains `index.json` and content-addressed assets. All published
history and current pointers are retained. Identical GLBs/stills are stored once
across annotation-only releases. Each geometry includes its GLB, four 1080p
previews, and four 4K PNGs. Editable scenes, source-document full text, draft
candidates, jobs, credentials, and backups stay local. Public supporting
passages and review notes remain visible.

## Upload and select a snapshot

Sign in to the GitHub CLI with your account, then upload the reviewed bundle:

```sh
gh release create pages-2026-09-14 \
  data/pages-export/2026-09-14/pages-archive.tar.gz \
  --repo prayag2301/f1-engineering-dashboard \
  --target codex/github-pages-release \
  --title 'Reviewed archive — 14 September 2026' \
  --notes 'Published Ferrari and Mercedes configurations with complete history.' \
  --latest=false
python3 scripts/pages.py pin \
  --bundle data/pages-export/2026-09-14/pages-archive.tar.gz \
  --release pages-2026-09-14
git add data/pages/snapshot.json
git commit -m 'Update reviewed Pages snapshot'
git push origin codex/github-pages-release
```

Use a new unique tag each time, and never replace an existing tag's assets.
Large files stay outside Git history. CI checks both the compressed bundle SHA
and every extracted asset. An 850 MiB archive cap leaves room for the application
within GitHub Pages' 1 GB site limit. Growth beyond that requires an explicit
storage decision; older history is never silently removed.

## Handover from the existing site

`.github/workflows/deploy-pages.yml` builds on pushes to the new branch and
`main`, and on pull requests. It runs archive tests, static export, browser
checks, and checksum validation, then uploads a downloadable static artifact.
Deployment additionally requires reviewed baselines for both teams and a branch
matching the repository variable `PAGES_DEPLOY_BRANCH`.

This repository already uses GitHub Actions for Pages. After the replacement's
first passing build, allow `codex/github-pages-release` in the `github-pages`
environment's deployment branch rules and set `PAGES_DEPLOY_BRANCH` to that name.
These settings prepare the handover; the empty-snapshot check still prevents
deployment. The first push with a valid pin replaces the site through
`actions/deploy-pages`.

Verify the deployment URL, `/deployment.json` (commit identity), both models,
direct team routes, and a 4K download. Then disable the old **Deploy static demo
to GitHub Pages** workflow and remove `demo/static` from the environment's allowed
branches so a later old-branch push cannot replace the new site. Retain that
branch for recovery. No force-push or deletion of history is needed.

After merging into `main`, allow `main` in the environment, move
`PAGES_DEPLOY_BRANCH` to `main`, and remove the temporary branch allowance.

## Rollback and failures

- Failed builds, downloads, checksums, and browser tests cannot deploy.
- A missing first baseline produces a build artifact and a deployment-deferred
  summary; the existing site stays live.
- To restore earlier public content, revert the snapshot descriptor to its
  previous tag/hash and push. Keep earlier GitHub Release bundles.
- To revert a team's current configuration, roll back its pointer locally,
  export a new snapshot, and deploy it. Historical comparisons remain available.
- Revert an application commit and redeploy to undo a code change. Do not rewrite
  a deployed branch or delete releases.

Docker must be running for the weekly scheduler. The Mac's containerized still
rendering uses CPU; the interactive viewer uses browser graphics.

References: [Next.js static exports](https://nextjs.org/docs/14/app/building-your-application/deploying/static-exports),
[Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
