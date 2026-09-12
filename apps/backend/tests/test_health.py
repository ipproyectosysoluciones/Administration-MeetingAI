def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_rejects_other_methods(client):
    resp = client.post("/health")
    assert resp.status_code == 405
