from pytest import approx


def test_healthcheck(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_metadata(client):
    response = client.get("/api/metadata")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["jurisdictions"] == [{"code": "BC", "name": "British Columbia"}]
    assert 2 in payload["supportedChildren"]


def test_child_support_route(client):
    response = client.post(
        "/api/calculate/child-support",
        json={
            "jurisdiction": "BC",
            "children": 3,
            "payorIncome": 200000,
            "recipientIncome": 54078.54,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["payorMonthly"] == approx(3582.0, rel=1e-4)
    assert payload["recipientMonthly"] == approx(1105.46, rel=1e-4)
    assert payload["netMonthly"] == approx(2476.54, rel=1e-4)


def test_spousal_support_rejects_invalid_target_range(client):
    response = client.post(
        "/api/calculate/spousal-support",
        json={
            "jurisdiction": "BC",
            "children": 2,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "targetMinPercent": 46,
            "targetMaxPercent": 40,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "'targetMinPercent' must be less than 'targetMaxPercent'."
