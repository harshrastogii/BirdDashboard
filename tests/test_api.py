"""
API integration tests (Phase 3a) — exercise the HTTP surface end-to-end
against the seeded metadata database via FastAPI's TestClient.

    python tests/test_api.py      # plain runner
    pytest tests/test_api.py      # if pytest is installed

Assumes the dev database has been migrated and seeded:
    alembic upgrade head && python -m api.seed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_readyz_checks_db():
    r = client.get("/api/v1/readyz")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def test_version_lists_models():
    r = client.get("/api/v1/version")
    assert r.status_code == 200
    body = r.json()
    assert body["api_major"] == "v1"
    keys = {m["key"] for m in body["models"]}
    assert {"birdnet", "nt_cnn", "multi_species"} <= keys


def test_species_list_shape():
    r = client.get("/api/v1/species")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "next_cursor" in body and "limit" in body
    assert len(body["items"]) > 0
    assert "common_name" in body["items"][0]


def test_recordings_list_has_links():
    r = client.get("/api/v1/recordings")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0
    rec = items[0]
    assert rec["audio_url"].endswith("/audio")
    assert rec["detections_url"].endswith("/detections")


def test_recording_detail_and_detections():
    rid = client.get("/api/v1/recordings").json()["items"][0]["id"]
    assert client.get(f"/api/v1/recordings/{rid}").status_code == 200
    d = client.get(f"/api/v1/recordings/{rid}/detections")
    assert d.status_code == 200 and isinstance(d.json(), list)


def test_pagination_cursor():
    r1 = client.get("/api/v1/recordings", params={"limit": 5})
    body1 = r1.json()
    assert len(body1["items"]) == 5
    assert body1["next_cursor"] is not None
    r2 = client.get("/api/v1/recordings", params={"limit": 5, "cursor": body1["next_cursor"]})
    ids1 = {i["id"] for i in body1["items"]}
    ids2 = {i["id"] for i in r2.json()["items"]}
    assert ids1.isdisjoint(ids2)   # no overlap across pages


def test_not_found_is_problem_json():
    r = client.get("/api/v1/recordings/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "NOT_FOUND" and body["status"] == 404
    assert body["request_id"]


def test_invalid_uuid_is_validation_error():
    r = client.get("/api/v1/recordings/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_forbidden_scope_returns_problem():
    # An 'agency' role lacks annotations:write; hit a read that agency DOES have
    # to confirm role plumbing, then confirm a missing scope is enforced.
    r = client.get("/api/v1/species", headers={"X-Debug-Role": "agency"})
    assert r.status_code == 200
    # 'sensor' role lacks species:read -> 403 Problem.
    r2 = client.get("/api/v1/species", headers={"X-Debug-Role": "sensor"})
    assert r2.status_code == 403 and r2.json()["code"] == "FORBIDDEN"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
