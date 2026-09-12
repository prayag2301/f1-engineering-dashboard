# Car archive and review studio

This is the canonical Next.js frontend. Run `npm ci`, `npm run typecheck`, and `npm run build`. Docker runs the standalone production output.

Browser requests use same-origin `/api/v1` rewrites to the FastAPI service. No review secret is included in the JavaScript bundle. The GLB viewer is keyed by immutable version ID and uses only that version's still when loading fails.

For GitHub Pages, run `npm run build:pages`. This exports a static site under the
repository subpath and reads a pinned JSON/asset snapshot instead of `/api/v1`.
Run `npm run test:pages` for the static browser checks. See the
[export and deployment guide](../docs/github-pages.md). Standard `npm run build`
retains the standalone Docker application and authenticated review studio.

Run `E2E_BASE_URL=http://127.0.0.1:3000 npm run test:e2e` against a running stack. The browser suite uses explicit synthetic manifests for public comparison tests; it never publishes a draft. Set `PLAYWRIGHT_CHROME_PATH` to an installed Chrome executable or install Playwright's Chromium.
