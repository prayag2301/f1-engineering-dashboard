"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { createCameraBus } from "./CarViewer";
import TeamComparison from "./TeamComparison";
import {
  request,
  mutate,
  dateLabel,
  type Catalog,
  type CarVersion,
  type Candidate,
  type Dashboard,
  type TeamKey,
  type ViewName,
} from "@/lib/releases";
const CarViewer = dynamic(() => import("./CarViewer"), { ssr: false });
const VIEWS: ViewName[] = ["front", "side", "rear", "three_quarter"];
const localDate = (date: string) => new Date(date).toISOString().slice(0, 16);

export default function ReviewStudio() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [token, setToken] = useState("");
  const [data, setData] = useState<Dashboard | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("drafts");
  const [selected, setSelected] = useState("");
  const refresh = useCallback(async () => {
    const [dashboard, cat] = await Promise.all([
      request<Dashboard>("/review/dashboard"),
      request<Catalog>("/cars/catalog"),
    ]);
    setData(dashboard);
    setCatalog(cat);
  }, []);
  useEffect(() => {
    request<{ authenticated: boolean }>("/review/session")
      .then((v) => setAuthenticated(v.authenticated))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    refresh().catch((e) => setError(e.message));
    const timer = setInterval(() => refresh().catch(() => {}), 10000);
    return () => clearInterval(timer);
  }, [authenticated, refresh]);
  async function action(work: () => Promise<unknown>, message = "Saved.") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function login(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await mutate("/review/session", { token });
      setToken("");
      setAuthenticated(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    setBusy(true);
    try {
      await request("/review/session", { method: "DELETE" });
      setAuthenticated(false);
      setData(null);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (authenticated !== true)
    return (
      <div className="login-card">
        <p className="eyebrow">MAINTAINER ACCESS</p>
        <h1>Review studio.</h1>
        <p>
          Inspect the evidence and car surfaces before they enter the public
          archive.
        </p>
        <form onSubmit={login}>
          <label>
            Review token
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button
            className="button primary"
            disabled={busy || authenticated === null}
          >
            {authenticated === null ? "Checking session…" : "Sign in"}
          </button>
        </form>
        <p className="muted">Use the ADMIN_TOKEN in your local .env file.</p>
        {error && (
          <p role="alert" className="notice error">
            {error}
          </p>
        )}
      </div>
    );
  const version =
    data?.versions.find((v) => v.id === selected) ??
    data?.versions.find((v) => v.status !== "published") ??
    data?.versions[0];
  return (
    <div className="review-studio">
      <div className="review-heading">
        <div>
          <p className="eyebrow">EVIDENCE → RECONSTRUCTION → RELEASE</p>
          <h1>Review studio.</h1>
          <p className="lede">
            A publication records what you can substantiate.
          </p>
        </div>
        <button onClick={logout}>Sign out</button>
      </div>
      <div className="review-tabs" role="tablist" aria-label="Review sections">
        {[
          ["drafts", "Car drafts"],
          ["evidence", "Source inbox"],
          ["release", "New release"],
          ["jobs", "Jobs & history"],
        ].map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "selected" : ""}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <div role="alert" className="notice error">
          {error}
        </div>
      )}
      {notice && (
        <div role="status" className="notice">
          {notice}
        </div>
      )}
      {!data || !catalog ? (
        <p role="status">Loading review workspace…</p>
      ) : (
        <>
          {tab === "drafts" && (
            <div className="review-layout">
              <aside className="draft-list">
                <div className="section-label">
                  CONFIGURATIONS <span>{data.versions.length}</span>
                </div>
                {data.versions.map((v) => (
                  <button
                    className={
                      version?.id === v.id
                        ? "draft-item selected"
                        : "draft-item"
                    }
                    key={v.id}
                    onClick={() => setSelected(v.id)}
                  >
                    <span className={`status-tag ${v.status}`}>{v.status}</span>
                    <strong>{catalog.teams[v.team_key].car_name}</strong>
                    <span>{v.label}</span>
                    <small>{dateLabel(v.as_of)}</small>
                  </button>
                ))}
              </aside>
              {version && (
                <DraftReview
                  key={version.id + version.status}
                  version={version}
                  comparisons={data.versions}
                  allowBaselineRevision={
                    !data.versions.some(
                      (v) =>
                        v.team_key === version.team_key &&
                        v.status === "published",
                    )
                  }
                  busy={busy}
                  action={action}
                />
              )}
            </div>
          )}
          {tab === "evidence" && (
            <div className="source-workspace">
              <SourceImportForm busy={busy} action={action} />
              <div>
                <div className="section-label">
                  CANDIDATES{" "}
                  <span>
                    {data.candidates.filter((c) => c.status === "draft").length}{" "}
                    awaiting review
                  </span>
                </div>
                {data.candidates.length === 0 ? (
                  <div className="empty-card">
                    <h2>No candidates yet.</h2>
                    <p>
                      Import a technical article or collect the configured
                      public sources. Claims arrive as drafts.
                    </p>
                  </div>
                ) : (
                  data.candidates.map((c) => (
                    <CandidateForm
                      key={c.id + c.status}
                      candidate={c}
                      catalog={catalog}
                      busy={busy}
                      action={action}
                    />
                  ))
                )}
              </div>
            </div>
          )}
          {tab === "release" && (
            <NewReleaseForm
              catalog={catalog}
              data={data}
              busy={busy}
              action={action}
              onCreated={(id) => {
                setSelected(id);
                setTab("drafts");
              }}
            />
          )}
          {tab === "jobs" && (
            <div>
              <div className="section-label">
                BUILD & COLLECTION JOBS{" "}
                <span>Monday / 10:00 Europe/Berlin</span>
              </div>
              <p className="muted">
                Jobs run while Docker is running. The scheduler catches up once
                after downtime. Collection never publishes a car.
              </p>
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  action(() => mutate("/review/collect"), "Collection queued.")
                }
              >
                Collect sources now
              </button>
              <div className="job-list">
                {data.jobs.map((job) => (
                  <article className="job-card" key={job.id}>
                    <div>
                      <strong>
                        {job.kind === "build"
                          ? "Car build"
                          : "Source collection"}
                      </strong>
                      <span className={`status-tag ${job.status}`}>
                        {job.status}
                      </span>
                    </div>
                    <small>
                      {dateLabel(job.created_at)} · Attempt {job.attempts}
                    </small>
                    {job.error && <pre className="job-error">{job.error}</pre>}
                    {Object.keys(job.result).length > 0 && (
                      <details>
                        <summary>Job result</summary>
                        <pre>{JSON.stringify(job.result, null, 2)}</pre>
                      </details>
                    )}
                    {job.status === "failed" && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          action(
                            () => mutate(`/review/jobs/${job.id}/retry`),
                            "Retry queued.",
                          )
                        }
                      >
                        Retry job
                      </button>
                    )}
                  </article>
                ))}
              </div>
              <div className="section-label">REVIEW HISTORY</div>
              {data.audit.map((a, i) => (
                <div className="audit-row" key={i}>
                  <span>{a.action.replaceAll("_", " ")}</span>
                  <code>{a.target_id.slice(0, 8)}</code>
                  <small>{dateLabel(a.created_at)}</small>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

type Action = (work: () => Promise<unknown>, message?: string) => Promise<void>;

function DraftReview({
  version,
  comparisons,
  allowBaselineRevision,
  busy,
  action,
}: {
  version: CarVersion;
  comparisons: CarVersion[];
  allowBaselineRevision: boolean;
  busy: boolean;
  action: Action;
}) {
  const [views, setViews] = useState<Record<ViewName, boolean>>({
    front: !!version.visual_review.front,
    side: !!version.visual_review.side,
    rear: !!version.visual_review.rear,
    three_quarter: !!version.visual_review.three_quarter,
  });
  const [notes, setNotes] = useState(version.visual_review.notes ?? "");
  const [referenceUrls, setReferenceUrls] = useState(
    (
      version.visual_review.reference_urls ??
      version.manifest.sources.map((s) => s.url)
    ).join("\n"),
  );
  const [rollbackReason, setRollbackReason] = useState("");
  const [neutral, setNeutral] = useState(false);
  const [detail, setDetail] = useState("");
  const [compareOther, setCompareOther] = useState(false);
  const [preset, setPreset] = useState<ViewName>("three_quarter");
  const [resetIndex, setResetIndex] = useState(0);
  const [bus] = useState(createCameraBus);
  const canCompare = comparisons.some(
    (v) =>
      v.team_key !== version.team_key &&
      ["ready", "published"].includes(v.status) &&
      v.manifest.assets.glb,
  );
  return (
    <section className="draft-review">
      <div className="draft-title">
        <div>
          <p className="eyebrow">
            {version.team_key.toUpperCase()} / {dateLabel(version.as_of)}
          </p>
          <h2>{version.label}</h2>
          <p>{version.configuration_event}</p>
        </div>
        <span className={`status-tag ${version.status}`}>{version.status}</span>
      </div>
      <div className="notice">
        {version.manifest.reconstruction_notice} This configuration is dated{" "}
        {dateLabel(version.as_of)}.
      </div>
      {version.manifest.assets.glb ? (
        <>
          {compareOther ? (
            <TeamComparison
              version={version}
              comparisons={comparisons}
              preset={preset}
              resetIndex={resetIndex}
              active={detail || null}
              onSelect={setDetail}
              focus={!!detail}
              bus={bus}
              neutral={neutral}
              isolate={false}
            />
          ) : (
            <CarViewer
              version={version}
              preset={preset}
              resetIndex={resetIndex}
              cameraBus={bus}
              height="480px"
              neutral={neutral}
              activeComponent={detail || null}
              onSelectComponent={setDetail}
              focus={!!detail}
            />
          )}
          <div className="shape-tools">
            <button
              type="button"
              disabled={!canCompare}
              aria-pressed={compareOther}
              onClick={() => setCompareOther((v) => !v)}
            >
              Compare other constructor
            </button>
            <button
              type="button"
              aria-pressed={neutral}
              onClick={() => setNeutral((v) => !v)}
            >
              Neutral surfaces
            </button>
            <select
              aria-label="Draft component detail"
              value={detail}
              onChange={(e) => setDetail(e.target.value)}
            >
              <option value="">Complete car</option>
              {Object.entries(version.manifest.components).map(([key, c]) => (
                <option value={key} key={key}>
                  {c.label}
                </option>
              ))}
            </select>
            <select
              aria-label="Draft camera view"
              value={preset}
              onChange={(e) => {
                setPreset(e.target.value as ViewName);
                setResetIndex((v) => v + 1);
              }}
            >
              {VIEWS.map((view) => (
                <option key={view} value={view}>
                  {view.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
          {detail && (
            <p className="uncertainty">
              {version.manifest.components[detail]?.uncertainty}
            </p>
          )}
        </>
      ) : (
        <div className="empty-card">
          <h3>
            {version.status === "building"
              ? "Building the complete car…"
              : "No validated render yet."}
          </h3>
          <p>
            The worker exports the geometry, source scene, four previews, and
            four 4K renders. Check Jobs & history for progress or errors.
          </p>
        </div>
      )}
      <div className="draft-actions">
        {allowBaselineRevision &&
          version.status === "ready" &&
          !version.parent_id && (
            <button
              disabled={busy}
              onClick={() =>
                action(
                  () => mutate(`/models/${version.team_key}/regenerate`),
                  "A new baseline draft is building from the current modeling catalog. The previous draft remains available.",
                )
              }
            >
              Build revised baseline
            </button>
          )}
        {["draft", "failed"].includes(version.status) && (
          <button
            disabled={busy}
            className="button primary"
            onClick={() =>
              action(
                () => mutate(`/review/versions/${version.id}/build`),
                "Build queued.",
              )
            }
          >
            Build draft
          </button>
        )}
        {version.manifest.assets.source && (
          <a className="button" href={version.manifest.assets.source.url}>
            Download editable Blender scene ↓
          </a>
        )}
      </div>
      <div className="section-label">REFERENCE MATERIAL</div>
      <div className="reference-links">
        {version.manifest.sources.map((source) => (
          <div key={source.id}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title} ↗
            </a>
            <p>
              {source.publisher} ·{" "}
              {source.published_at
                ? dateLabel(source.published_at)
                : "Publication date unresolved"}
            </p>
            {source.image_urls.map((url, i) => (
              <a
                className="image-ref"
                href={url}
                target="_blank"
                rel="noreferrer"
                key={url}
              >
                Reference photograph {i + 1} ↗
              </a>
            ))}
          </div>
        ))}
      </div>
      <details className="component-evidence">
        <summary>Component revisions and uncertainty</summary>
        {Object.entries(version.manifest.components).map(([key, c]) => (
          <div key={key}>
            <strong>{c.label}</strong>
            <p>{c.uncertainty}</p>
            <code>{JSON.stringify(c.parameters)}</code>
          </div>
        ))}
      </details>
      {version.status === "ready" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action(
              () =>
                mutate(
                  `/review/versions/${version.id}/visual-review`,
                  {
                    ...views,
                    notes,
                    reference_urls: referenceUrls
                      .split("\n")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  },
                  "PUT",
                ),
              "Visual review saved. Publication is now available if all four views are checked.",
            );
          }}
        >
          <div className="section-label">FOUR-VIEW REFERENCE COMPARISON</div>
          <p>
            Check each view only after comparing its silhouette and visible
            details against dated references. Leave it unchecked if the evidence
            is insufficient.
          </p>
          <div className="review-views">
            {VIEWS.map((view) => (
              <label key={view}>
                <img
                  src={version.manifest.assets[`preview_${view}`]?.url}
                  alt={`${view.replaceAll("_", " ")} draft render`}
                />
                <span>
                  <input
                    type="checkbox"
                    checked={views[view]}
                    onChange={(e) =>
                      setViews((v) => ({ ...v, [view]: e.target.checked }))
                    }
                  />
                  {view.replaceAll("_", " ")} matches the cited references
                </span>
                <a
                  href={version.manifest.assets[`render_${view}`]?.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Inspect 4K ↗
                </a>
              </label>
            ))}
          </div>
          <label>
            Reference URLs used for this review, one per line
            <textarea
              value={referenceUrls}
              onChange={(e) => setReferenceUrls(e.target.value)}
              required
            />
          </label>
          <label>
            Assessment and remaining uncertainty
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              minLength={20}
              required
              placeholder="Describe the visible details checked and any remaining approximations."
            />
          </label>
          <button className="button" disabled={busy}>
            Save visual review
          </button>
        </form>
      )}
      {version.status === "ready" && (
        <div className="publish-panel">
          <div>
            <h3>Publish this configuration</h3>
            <p>
              All artifacts and reference checks are validated again. The
              existing published version stays available in history.
            </p>
          </div>
          <button
            className="button primary"
            disabled={busy || !VIEWS.every((v) => version.visual_review[v])}
            onClick={() =>
              action(
                () => mutate(`/review/versions/${version.id}/publish`),
                "Release published. It is now visible in the car archive.",
              )
            }
          >
            Publish release ↗
          </button>
        </div>
      )}
      {version.status === "published" && (
        <form
          className="publish-panel"
          onSubmit={(e) => {
            e.preventDefault();
            action(
              () =>
                mutate(`/review/cars/${version.team_key}/rollback`, {
                  version_id: version.id,
                  reason: rollbackReason,
                }),
              "Current release pointer updated; history preserved.",
            );
          }}
        >
          <label>
            Reason for making this the current release
            <input
              value={rollbackReason}
              onChange={(e) => setRollbackReason(e.target.value)}
              minLength={5}
              required
            />
          </label>
          <button disabled={busy} className="button">
            Use this published version
          </button>
        </form>
      )}
    </section>
  );
}

function SourceImportForm({ busy, action }: { busy: boolean; action: Action }) {
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [publisher, setPublisher] = useState("");
  const [date, setDate] = useState("");
  const [event, setEvent] = useState("");
  return (
    <aside className="source-import">
      <p className="eyebrow">NEW EVIDENCE</p>
      <h2>Bring the source.</h2>
      <p>
        Use an article or FIA submission URL. Paste text when a publisher blocks
        automated access.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          action(
            () =>
              mutate("/review/sources", {
                url,
                ...(text ? { text } : {}),
                ...(title ? { title } : {}),
                ...(publisher ? { publisher } : {}),
                ...(date
                  ? { published_at: new Date(date + "Z").toISOString() }
                  : {}),
                ...(event ? { event_name: event } : {}),
              }),
            "Source imported. Review its candidate claims below.",
          );
        }}
      >
        <label>
          Source URL
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </label>
        <label>
          Title (optional)
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Publisher (optional)
          <input
            value={publisher}
            onChange={(e) => setPublisher(e.target.value)}
          />
        </label>
        <label>
          Publication date (UTC, if known)
          <input
            type="datetime-local"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <label>
          Event or configuration (if stated)
          <input
            value={event}
            onChange={(e) => setEvent(e.target.value)}
            placeholder="e.g. Italian Grand Prix — qualifying"
          />
        </label>
        <label>
          Article text (optional)
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
          />
        </label>
        <button disabled={busy} className="button primary">
          Import as draft evidence
        </button>
      </form>
      <button
        disabled={busy}
        onClick={() =>
          action(
            () => mutate("/review/collect"),
            "Collection queued; see Jobs & history.",
          )
        }
      >
        Collect configured sources
      </button>
    </aside>
  );
}

function CandidateForm({
  candidate,
  catalog,
  busy,
  action,
}: {
  candidate: Candidate;
  catalog: Catalog;
  busy: boolean;
  action: Action;
}) {
  const [c, setC] = useState(candidate);
  const [date, setDate] = useState(
    c.observed_at ? localDate(c.observed_at) : "",
  );
  function save(status: string) {
    return action(
      () =>
        mutate(
          `/review/candidates/${c.id}`,
          {
            team_key: c.team_key,
            component: c.component,
            event_name: c.event_name,
            observed_at: date ? new Date(date + "Z").toISOString() : null,
            summary: c.summary,
            supporting_passage: c.supporting_passage,
            page: c.page,
            evidence_status: c.evidence_status,
            representation: c.representation,
            review_notes: c.review_notes,
            status,
          },
          "PATCH",
        ),
      `Candidate ${status}.`,
    );
  }
  return (
    <details className="candidate-card">
      <summary>
        <span className={`status-tag ${c.status}`}>{c.status}</span>
        <strong>{c.summary}</strong>
        <small>{c.source?.publisher}</small>
      </summary>
      <div className="candidate-fields">
        <a href={c.source?.url} target="_blank" rel="noreferrer">
          Open original source ↗
        </a>
        <div className="form-grid">
          <label>
            Team
            <select
              value={c.team_key ?? ""}
              onChange={(e) =>
                setC({
                  ...c,
                  team_key: (e.target.value || null) as TeamKey | null,
                })
              }
            >
              <option value="">Unresolved</option>
              <option value="ferrari">Ferrari</option>
              <option value="mercedes">Mercedes</option>
            </select>
          </label>
          <label>
            Component
            <select
              value={c.component ?? ""}
              onChange={(e) =>
                setC({ ...c, component: e.target.value || null })
              }
            >
              <option value="">Unresolved</option>
              {Object.entries(catalog.components).map(([key, v]) => (
                <option key={key} value={key}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Observed configuration date (UTC)
            <input
              type="datetime-local"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label>
            Event / session
            <input
              value={c.event_name ?? ""}
              onChange={(e) => setC({ ...c, event_name: e.target.value })}
            />
          </label>
          <label>
            Evidence status
            <select
              value={c.evidence_status}
              onChange={(e) =>
                setC({
                  ...c,
                  evidence_status: e.target
                    .value as Candidate["evidence_status"],
                })
              }
            >
              {["unverified", "reported", "confirmed", "conflicting"].map(
                (v) => (
                  <option key={v}>{v}</option>
                ),
              )}
            </select>
          </label>
          <label>
            Representation
            <select
              value={c.representation}
              onChange={(e) =>
                setC({
                  ...c,
                  representation: e.target.value as Candidate["representation"],
                })
              }
            >
              <option value="annotation_only">Highlight + explanation</option>
              <option value="modeled">Confirmed shape reconstruction</option>
            </select>
          </label>
        </div>
        <label>
          PDF page (if applicable)
          <input
            type="number"
            min={1}
            max={250}
            value={c.page ?? ""}
            onChange={(e) =>
              setC({
                ...c,
                page: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Summary
          <textarea
            value={c.summary}
            onChange={(e) => setC({ ...c, summary: e.target.value })}
          />
        </label>
        <label>
          Supporting passage{c.page ? ` (page ${c.page})` : ""}
          <textarea
            value={c.supporting_passage}
            onChange={(e) => setC({ ...c, supporting_passage: e.target.value })}
          />
        </label>
        <label>
          Review notes / visual evidence
          <textarea
            value={c.review_notes}
            onChange={(e) => setC({ ...c, review_notes: e.target.value })}
          />
        </label>
        <div className="draft-actions">
          <button disabled={busy} onClick={() => save("draft")}>
            Save draft
          </button>
          <button disabled={busy} onClick={() => save("rejected")}>
            Reject claim
          </button>
          <button
            disabled={busy}
            className="button primary"
            onClick={() => save("approved")}
          >
            Approve evidence
          </button>
        </div>
      </div>
    </details>
  );
}

function NewReleaseForm({
  catalog,
  data,
  busy,
  action,
  onCreated,
}: {
  catalog: Catalog;
  data: Dashboard;
  busy: boolean;
  action: Action;
  onCreated: (id: string) => void;
}) {
  const [kind, setKind] = useState("evolution");
  const [corrections, setCorrections] = useState<string[]>([]);
  const [reversion, setReversion] = useState("");
  const [team, setTeam] = useState<TeamKey>("ferrari");
  const [parentId, setParentId] = useState("");
  const [label, setLabel] = useState("");
  const [event, setEvent] = useState("");
  const [date, setDate] = useState(localDate(new Date().toISOString()));
  const [cutoff, setCutoff] = useState(localDate(new Date().toISOString()));
  const [ids, setIds] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [parameters, setParameters] = useState<
    Record<string, Record<string, number>>
  >({});
  const [uncertainty, setUncertainty] = useState<Record<string, string>>({});
  const parents = data.versions.filter(
    (v) => v.team_key === team && v.status === "published",
  );
  const parent = parents.find((v) => v.id === parentId) ?? parents[0];
  const candidates = data.candidates.filter(
    (c) => c.team_key === team && c.status === "approved",
  );
  const chosen = candidates.filter((c) => ids.includes(c.id));
  const modeled =
    kind === "reconstruction"
      ? corrections
      : Array.from(
          new Set(
            chosen
              .filter((c) => c.representation === "modeled")
              .map((c) => c.component!),
          ),
        );
  async function submit(e: FormEvent) {
    e.preventDefault();
    await action(async () => {
      const version = await mutate<CarVersion>("/review/versions", {
        team_key: team,
        parent_id: parent?.id,
        label,
        configuration_event:
          kind === "reconstruction" ? parent?.configuration_event : event,
        configuration_kind: kind,
        ...(kind === "reversion" ? { reverts_to_id: reversion } : {}),
        as_of:
          kind === "reconstruction"
            ? parent?.as_of
            : new Date(date + "Z").toISOString(),
        evidence_cutoff: new Date(cutoff + "Z").toISOString(),
        candidate_ids: kind === "reconstruction" ? [] : ids,
        notes,
        revisions: (kind === "reversion" ? [] : modeled).map((component) => ({
          component,
          parameters:
            parameters[component] ??
            parent?.manifest.components[component].parameters ??
            {},
          source_ids:
            kind === "reconstruction"
              ? parent?.manifest.components[component].source_ids
              : Array.from(
                  new Set(
                    chosen
                      .filter((c) => c.component === component)
                      .map((c) => c.source_id),
                  ),
                ),
          uncertainty: uncertainty[component] ?? "",
        })),
      });
      onCreated(version.id);
    }, "Draft configuration created. Build it, inspect its references, then publish.");
  }
  return (
    <form className="new-release-form" onSubmit={submit}>
      <p className="eyebrow">VERSIONED CONFIGURATION</p>
      <h2>Compose the next release.</h2>
      <p>
        Start from a published car. Only explicitly revised components change;
        annotation-only claims carry the previous geometry forward.
      </p>
      <div className="form-grid">
        <label>
          Team
          <select
            value={team}
            onChange={(e) => {
              setTeam(e.target.value as TeamKey);
              setParentId("");
              setIds([]);
              setParameters({});
              setUncertainty({});
            }}
          >
            <option value="ferrari">Ferrari</option>
            <option value="mercedes">Mercedes</option>
          </select>
        </label>
        <label>
          Parent release
          <select
            value={parent?.id ?? ""}
            onChange={(e) => {
              setParentId(e.target.value);
              setParameters({});
            }}
          >
            {parents.length === 0 && (
              <option>Publish the reference baseline first</option>
            )}
            {parents.map((v) => (
              <option value={v.id} key={v.id}>
                {v.label} — {dateLabel(v.as_of)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Configuration type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="evolution">Development update</option>
            <option value="circuit_specific">
              Circuit-specific configuration
            </option>
            <option value="reversion">
              Return to a previous configuration
            </option>
            <option value="no_change">No new modeled change</option>
            <option value="reconstruction">
              Improve an existing reconstruction
            </option>
          </select>
        </label>
        {kind === "reversion" && (
          <label>
            Restore geometry from
            <select
              required
              value={reversion}
              onChange={(e) => setReversion(e.target.value)}
            >
              <option value="">Select an earlier release</option>
              {parents.map((v) => (
                <option value={v.id} key={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Release label
          <input
            required
            minLength={3}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Monza — qualifying configuration"
          />
        </label>
        <label>
          Event / session
          <input
            required
            minLength={3}
            disabled={kind === "reconstruction"}
            value={
              kind === "reconstruction"
                ? (parent?.configuration_event ?? "")
                : event
            }
            onChange={(e) => setEvent(e.target.value)}
          />
        </label>
        <label>
          Configuration observed (UTC)
          <input
            type="datetime-local"
            required
            disabled={kind === "reconstruction"}
            value={
              kind === "reconstruction"
                ? localDate(parent?.as_of ?? new Date().toISOString())
                : date
            }
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <label>
          Evidence cutoff (UTC)
          <input
            type="datetime-local"
            required
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value)}
          />
        </label>
      </div>
      <div className="section-label">
        {kind === "reconstruction"
          ? "ASSEMBLIES TO CORRECT"
          : "APPROVED CLAIMS"}
      </div>
      {kind === "reconstruction" ? (
        <>
          <p className="notice">
            Correct the model of the same dated car using its existing
            references. This is labeled as a reconstruction correction and does
            not claim a new racing upgrade. Every changed assembly still needs a
            visual review.
          </p>
          {Object.entries(catalog.components).map(([key, value]) => (
            <label className="candidate-check" key={key}>
              <input
                type="checkbox"
                checked={corrections.includes(key)}
                onChange={(e) =>
                  setCorrections(
                    e.target.checked
                      ? [...corrections, key]
                      : corrections.filter((c) => c !== key),
                  )
                }
              />
              <span>{value.label}</span>
            </label>
          ))}
        </>
      ) : candidates.length === 0 ? (
        <p className="muted">
          No approved claims. You can create a release that records no new
          modeled change.
        </p>
      ) : (
        candidates.map((c) => (
          <label className="candidate-check" key={c.id}>
            <input
              type="checkbox"
              checked={ids.includes(c.id)}
              onChange={(e) =>
                setIds(
                  e.target.checked
                    ? [...ids, c.id]
                    : ids.filter((id) => id !== c.id),
                )
              }
            />
            <span>
              {c.summary}
              <small>
                {c.representation === "modeled"
                  ? "Requires a component revision"
                  : "Geometry remains unchanged"}
              </small>
            </span>
          </label>
        ))
      )}
      {kind !== "reversion" &&
        modeled.map((component) => (
          <fieldset key={component}>
            <legend>
              {catalog.components[component].label} — explicit reconstruction
            </legend>
            <p>
              These parameters describe your reviewed reconstruction. They are
              never inferred from article keywords.
            </p>
            <div className="form-grid">
              {Object.entries(catalog.components[component].parameters).map(
                ([key, [min, max]]) => (
                  <label key={key}>
                    {key.replaceAll("_", " ")} (metres)
                    <input
                      type="number"
                      step="0.001"
                      min={min}
                      max={max}
                      required
                      value={
                        parameters[component]?.[key] ??
                        parent?.manifest.components[component].parameters[
                          key
                        ] ??
                        min
                      }
                      onChange={(e) =>
                        setParameters({
                          ...parameters,
                          [component]: {
                            ...parent?.manifest.components[component]
                              .parameters,
                            ...parameters[component],
                            [key]: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                ),
              )}
            </div>
            <label>
              Evidence-supported shape and remaining uncertainty
              <textarea
                required
                minLength={10}
                value={uncertainty[component] ?? ""}
                onChange={(e) =>
                  setUncertainty({
                    ...uncertainty,
                    [component]: e.target.value,
                  })
                }
              />
            </label>
          </fieldset>
        ))}
      <label>
        Release notes
        <textarea
          required={kind === "reconstruction"}
          minLength={kind === "reconstruction" ? 20 : undefined}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      <button className="button primary" disabled={busy || !parent}>
        Create draft configuration
      </button>
    </form>
  );
}
