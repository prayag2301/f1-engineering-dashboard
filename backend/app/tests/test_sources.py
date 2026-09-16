from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock
import pytest
import httpx
from app.models.releases import SourceDocument, UpgradeCandidate
from app.schemas.releases import SourceImport
from app.services.sources import (
    import_source,
    extract_candidates,
    parse_document,
    check_remote,
    feed_links,
)


def document(text):
    return SourceDocument(id=uuid4(), text=text, pages=[])


def test_multiple_teams_and_components_are_drafts():
    rows = extract_candidates(
        document(
            "Ferrari introduced a new front wing and floor. Mercedes revised its rear wing."
        )
    )
    assert {(c.team_key, c.component) for c in rows} == {
        ("ferrari", "front_wing"),
        ("ferrari", "floor"),
        ("mercedes", "rear_wing"),
    }
    assert all(
        c.status == "draft"
        and c.evidence_status == "unverified"
        and c.observed_at is None
        for c in rows
    )


def test_ambiguous_story_never_invents_a_team_or_race():
    rows = extract_candidates(
        document("Ferrari and Mercedes introduced new floors and a revised front wing.")
    )
    assert rows and all(c.team_key is None and c.event_name is None for c in rows)


def test_fia_page_and_heading_context():
    source = document("")
    source.pages = [
        {
            "page": 3,
            "text": "Scuderia Ferrari\n\nRevised front wing endplate and new floor geometry.",
        }
    ]
    rows = extract_candidates(source)
    assert len(rows) == 2 and all(c.page == 3 and c.team_key == "ferrari" for c in rows)


def test_duplicate_tracking_query_story_is_not_reimported(db):
    payload = SourceImport(
        url="https://www.ferrari.com/news/update?utm_source=test",
        text="Ferrari introduced a revised front wing assembly for the current race.",
    )
    first, rows, duplicate = import_source(db, payload)
    db.commit()
    again, second, duplicate = import_source(
        db, payload.model_copy(update={"url": "https://www.ferrari.com/news/update"})
    )
    assert duplicate and again.id == first.id and second == []
    assert db.query(UpgradeCandidate).count() == 1


def test_missing_date_stays_unknown_and_manual_import_preserves_metadata(db):
    source, rows, _ = import_source(
        db,
        SourceImport(
            url="https://example.org/story",
            text="Mercedes introduced a revised floor for this race weekend.",
            publisher="Manual source",
            event_name="Monza",
        ),
    )
    assert source.published_at is None and source.retrieved_at
    assert rows[0].observed_at is None and rows[0].event_name == "Monza"


def test_blocked_fetch_and_cross_network_urls(monkeypatch):
    for url in (
        "http://localhost/internal",
        "http://127.0.0.1/",
        "file:///etc/passwd",
        "https://fia.com:8000/a",
        "https://fia.com@127.0.0.1/",
    ):
        with pytest.raises(ValueError):
            check_remote(url)
    monkeypatch.setattr(
        "app.services.sources.socket.getaddrinfo",
        lambda *a, **k: [(None, None, None, None, ("127.0.0.1", 443))],
    )
    with pytest.raises(ValueError):
        check_remote("https://fia.com/internal")
    with pytest.raises(ValueError):
        parse_document(b"<html>Access denied</html>", "text/html", "https://fia.com")


def test_failed_import_does_not_create_partial_evidence(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.sources.fetch_bytes",
        Mock(side_effect=httpx.ConnectError("blocked")),
    )
    with pytest.raises(httpx.ConnectError):
        import_source(db, SourceImport(url="https://fia.com/test"))
    assert db.query(SourceDocument).count() == 0


def test_html_publication_date_and_atom_feed():
    html = b'<html><title>Technical report</title><meta property="article:published_time" content="2026-03-01T12:00:00Z"><article><p>Ferrari introduced a new front wing at this event. The photographs show the changes to the outboard endplate and the profile of the flap.</p></article></html>'
    parsed = parse_document(html, "text/html", "https://formula1.com/technical")
    assert parsed["published_at"] == datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
    assert (
        feed_links(
            b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New wing</title><link href="https://fia.com/story"/></entry></feed>'
        )[0]["url"]
        == "https://fia.com/story"
    )


def test_conflicting_claim_cannot_be_approved(admin, db):
    source, rows, _ = import_source(
        db,
        SourceImport(
            url="https://fia.com/conflict",
            text="Ferrari reportedly revised the front wing, but the team disputes this change.",
        ),
    )
    db.commit()
    response = admin.patch(
        f"/api/v1/review/candidates/{rows[0].id}",
        json={
            "team_key": "ferrari",
            "component": "front_wing",
            "event_name": "Monza",
            "observed_at": "2026-09-01T00:00:00Z",
            "evidence_status": "conflicting",
            "status": "approved",
        },
    )
    assert response.status_code == 422


def test_approval_cannot_invent_supporting_passage(admin, db):
    _, rows, _ = import_source(
        db,
        SourceImport(
            url="https://fia.com/claim",
            text="Ferrari introduced a revised front wing endplate for this event.",
        ),
    )
    db.commit()
    response = admin.patch(
        f"/api/v1/review/candidates/{rows[0].id}",
        json={
            "team_key": "ferrari",
            "component": "front_wing",
            "event_name": "Monza",
            "observed_at": "2026-09-01T00:00:00Z",
            "evidence_status": "reported",
            "supporting_passage": "The new wing has a precise 300 millimetre chord.",
            "status": "approved",
        },
    )
    assert response.status_code == 422


def test_feed_dates_are_retained_as_fallbacks(db):
    item = feed_links(
        b"<rss><channel><item><title>Ferrari updates</title><link>https://fia.com/story</link><pubDate>Mon, 02 Mar 2026 10:00:00 GMT</pubDate></item></channel></rss>"
    )[0]
    assert item["published_at"] == datetime(2026, 3, 2, 10, tzinfo=timezone.utc)
    source, _, _ = import_source(
        db,
        SourceImport(
            url=item["url"],
            text="Ferrari revised its front wing at the current event.",
            fallback_published_at=item["published_at"],
        ),
    )
    assert source.published_at == item["published_at"]


def test_entire_collection_failure_is_retryable(settings, monkeypatch, tmp_path):
    import json
    from app import tasks

    (tmp_path / "sources.json").write_text(
        json.dumps({"sources": [{"url": "https://fia.com/feed", "kind": "feed"}]})
    )
    monkeypatch.setattr(settings, "REFERENCE_ROOT", tmp_path)
    monkeypatch.setattr(tasks, "heartbeat", Mock())
    monkeypatch.setattr(
        "app.services.sources.fetch_bytes",
        Mock(side_effect=httpx.ConnectError("blocked publisher")),
    )
    with pytest.raises(tasks.CollectionFailure) as failure:
        tasks.collect_sources(uuid4(), 1)
    assert (
        failure.value.result["coverage"] == "partial"
        and len(failure.value.result["errors"]) == 1
    )


def test_worker_import_registers_legacy_foreign_key_metadata():
    import subprocess, sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.tasks import BuildJob; from app.database import Base; assert 'upgrades' in {t.name for t in Base.metadata.sorted_tables}",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_unfamiliar_component_remains_an_unresolved_draft():
    rows = extract_candidates(
        document("Ferrari introduced a new thermal conditioning device.")
    )
    assert len(rows) == 1 and rows[0].team_key == "ferrari"
    assert rows[0].component is None and rows[0].status == "draft"


def test_fia_table_rows_keep_separate_claims_and_unfamiliar_labels():
    source = document("")
    source.source_type = "fia_submission"
    source.pages = [
        {
            "page": 4,
            "text": """Car Presentation – 2026 Spanish Grand Prix
Mercedes-AMG PETRONAS F1 Team
Updated
component
Primary reason for update
1
Rear Wing
Circuit specific - Drag Range
Rear wing central winglet span reduced.
2
Exhaust Tailpipe
Circuit specific - Drag Range
Additional winglet added behind exhaust.
3
Front Drum
Performance - Flow Conditioning
Front lip reprofiled to improve flow to the rear wing.
""",
        }
    ]
    rows = extract_candidates(source)
    assert len(rows) == 3
    assert [c.component for c in rows] == ["rear_wing", None, None]
    assert all(c.team_key == "mercedes" and c.page == 4 for c in rows)
    assert "Exhaust" not in rows[0].supporting_passage
    assert rows[1].supporting_passage.startswith("Exhaust Tailpipe")
