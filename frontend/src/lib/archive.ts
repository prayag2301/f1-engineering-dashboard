import {
  request,
  type Catalog,
  type CarVersion,
  type TeamKey,
} from "./releases";

export const staticArchive = process.env.NEXT_PUBLIC_STATIC_ARCHIVE === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
interface Snapshot {
  schema_version: 1;
  generated_at: string | null;
  catalog: Catalog;
  versions: Record<TeamKey, CarVersion[]>;
}

// One immutable snapshot per page session keeps the catalog and current pointers
// consistent during a deployment. An aborted reader must not cancel other readers.
let snapshot: Promise<Snapshot> | undefined;
async function readSnapshot(signal?: AbortSignal): Promise<Snapshot> {
  if (!snapshot) {
    snapshot = fetch(`${basePath}/archive/index.json`, { cache: "no-cache" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The release archive could not be loaded.");
        const data: Snapshot = await response.json();
        if (data.schema_version !== 1 || !data.catalog || !data.versions) {
          throw new Error("This release archive format is unsupported.");
        }
        for (const versions of Object.values(data.versions)) {
          for (const version of versions) {
            if (version.status !== "published")
              throw new Error("Unpublished release in public archive.");
            for (const asset of Object.values(version.manifest.assets)) {
              if (!/^assets\/[a-f0-9]{64}\.(glb|png)$/.test(asset.url)) {
                throw new Error("Invalid archive asset path.");
              }
              asset.url = `${basePath}/archive/${asset.url}`;
            }
          }
        }
        return data;
      })
      .catch((error) => {
        snapshot = undefined;
        throw error;
      });
  }
  const result = await snapshot;
  signal?.throwIfAborted();
  return result;
}

export async function readCatalog(signal?: AbortSignal): Promise<Catalog> {
  return staticArchive
    ? (await readSnapshot(signal)).catalog
    : request<Catalog>("/cars/catalog", { signal });
}
export async function readVersions(
  team: TeamKey,
  signal?: AbortSignal,
): Promise<CarVersion[]> {
  return staticArchive
    ? (await readSnapshot(signal)).versions[team]
    : request<CarVersion[]>(`/cars/${team}/versions?season=2026`, { signal });
}
