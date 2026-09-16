"""Release visibility and authorization replace the old procedural GLB contract."""

from uuid import UUID
from app.models.releases import CarVersion
from app.services.releases import bootstrap_baseline


def test_no_procedural_public_fallback(client):
    assert client.get("/api/v1/models/ferrari/latest.glb").status_code == 404
    assert client.head("/api/v1/models/ferrari/latest.glb").status_code == 404
    assert client.post("/api/v1/models/ferrari/regenerate").status_code == 401


def test_drafts_are_private(client, db):
    draft = bootstrap_baseline(db, "ferrari")
    db.commit()
    assert client.get("/api/v1/cars/ferrari/versions").json() == []
    assert client.get(f"/api/v1/cars/ferrari/versions/{draft.id}").status_code == 404
    assert client.get(f"/api/v1/releases/{draft.id}/car.glb").status_code == 404
    assert client.get("/api/v1/review/dashboard").status_code == 401


def test_regeneration_is_async_draft(admin, db):
    response = admin.post("/api/v1/models/mercedes/regenerate")
    assert response.status_code == 202, response.text
    version = db.get(CarVersion, UUID(response.json()["version_id"]))
    assert version.status == "building"
    assert admin.get("/api/v1/cars/mercedes/versions").json() == []
    again = admin.post("/api/v1/models/mercedes/regenerate")
    assert again.json()["id"] == response.json()["id"]


def test_cookie_auth_and_cross_site_rejection(client):
    route = "/api/v1/review/session"
    assert (
        client.post(route, json={"token": "test-maintainer-token"}).status_code == 403
    )
    assert (
        client.post(
            route, headers={"X-F1-Review": "1"}, json={"token": "incorrect"}
        ).status_code
        == 401
    )
    login = client.post(
        route, headers={"X-F1-Review": "1"}, json={"token": "test-maintainer-token"}
    )
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/v1/review/dashboard").status_code == 200
    assert client.post("/api/v1/review/collect").status_code == 403
    assert (
        client.post(
            "/api/v1/review/collect",
            headers={"X-F1-Review": "1", "Sec-Fetch-Site": "cross-site"},
        ).status_code
        == 403
    )
    assert client.delete(route, headers={"X-F1-Review": "1"}).status_code == 200
    assert client.get("/api/v1/review/dashboard").status_code == 401


def test_demo_routes_are_opt_in(admin):
    response = admin.post("/api/v1/seed/")
    assert response.status_code == 403


def test_ready_baseline_regeneration_creates_new_draft(admin, db):
    original = bootstrap_baseline(db, "ferrari")
    original.status = "ready"
    original.manifest = {
        **original.manifest,
        "assets": {"glb": {"url": "/immutable-original.glb"}},
    }
    db.commit()
    identity = original.id
    response = admin.post("/api/v1/models/ferrari/regenerate")
    assert response.status_code == 202, response.text
    assert response.json()["version_id"] != str(identity)
    again = admin.post("/api/v1/models/ferrari/regenerate")
    assert again.status_code == 202
    assert again.json()["id"] == response.json()["id"]
    db.refresh(original)
    assert original.status == "ready"
    assert original.manifest["assets"]["glb"]["url"] == "/immutable-original.glb"
    assert not original.visual_review
