from pytest import approx


def test_healthcheck(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_metadata(client):
    response = client.get("/api/metadata")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["jurisdictions"] == [
        {"code": "AB", "name": "Alberta"},
        {"code": "BC", "name": "British Columbia"},
        {"code": "MB", "name": "Manitoba"},
        {"code": "NB", "name": "New Brunswick"},
        {"code": "NL", "name": "Newfoundland and Labrador"},
        {"code": "NS", "name": "Nova Scotia"},
        {"code": "NT", "name": "Northwest Territories"},
        {"code": "NU", "name": "Nunavut"},
        {"code": "ON", "name": "Ontario"},
        {"code": "PE", "name": "Prince Edward Island"},
        {"code": "SK", "name": "Saskatchewan"},
        {"code": "YT", "name": "Yukon"},
    ]
    assert payload["spousalSupportJurisdictions"] == payload["jurisdictions"]
    assert payload["supportedChildren"] == [1, 2, 3, 4, 5, 6, 7]
    assert payload["sourceReferences"][0]["key"] == "childSupportTables"
    assert payload["sourceReferences"][1]["key"] == "taxRates"
    assert payload["defaultTaxYear"] == 2023
    assert "shared-custody" in payload["benefitAssumptions"]
    assert "non-Quebec" in payload["spousalSupportAssumptions"]


def test_child_support_route(client):
    response = client.post(
        "/api/calculate/child-support",
        json={
            "jurisdiction": "BC",
            "children": 3,
            "taxYear": 2025,
            "payorIncome": 200000,
            "recipientIncome": 54078.54,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["payorMonthly"] == approx(3582.0, rel=1e-4)
    assert payload["recipientMonthly"] == approx(1106.0, rel=1e-4)
    assert payload["netMonthly"] == approx(2476.0, rel=1e-4)
    assert payload["taxYear"] == 2025


def test_child_support_route_supports_ontario(client):
    response = client.post(
        "/api/calculate/child-support",
        json={
            "jurisdiction": "ON",
            "children": 3,
            "taxYear": 2025,
            "payorIncome": 200000,
            "recipientIncome": 54078.54,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["jurisdiction"] == "ON"
    assert payload["payorMonthly"] == approx(3428.0, rel=1e-4)


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


def test_spousal_support_route_supports_ontario(client):
    response = client.post(
        "/api/calculate/spousal-support",
        json={
            "jurisdiction": "ON",
            "children": 2,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "targetMinPercent": 40,
            "targetMaxPercent": 46,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["jurisdiction"] == "ON"
    assert payload["estimatedSpousalSupportAnnual"] > 0
    assert payload["benefits"]["lineItems"] == [
        {"key": "canadaChildBenefitAnnual", "label": "Canada child benefit"},
        {"key": "gstHstCreditAnnual", "label": "GST/HST credit"},
    ]


def test_spousal_support_route_accepts_tax_year(client):
    response = client.post(
        "/api/calculate/spousal-support",
        json={
            "jurisdiction": "BC",
            "children": 2,
            "childrenUnderSix": 1,
            "taxYear": 2025,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "targetMinPercent": 40,
            "targetMaxPercent": 46,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["taxYear"] == 2025
    assert payload["childrenUnderSix"] == 1
    assert payload["childSupport"]["children"] == 2
    assert payload["ndiChildSupport"]["children"] == 2
    assert payload["payorTax"] > 0
    assert payload["payorTaxBeforeSupportDeduction"] > payload["payorTax"]
    assert payload["recipientTax"] > payload["recipientTaxBeforeSupportInclusion"]
    assert payload["recipientTaxSupportCost"] > 0
    assert payload["payorTaxProfile"]["payrollDeductions"] > 0
    assert payload["payorTaxProfile"]["incomeTax"] > 0
    assert payload["payorTaxProfile"]["totalDeductions"] == payload["payorTax"]
    assert payload["benefits"]["recipient"]["totalAnnual"] > 0
    assert payload["payorEquivalentBeforeTaxIncome"] > 0
    assert payload["recipientEquivalentBeforeTaxIncome"] > 0


def test_spousal_support_route_accepts_separate_spousal_incomes(client):
    response = client.post(
        "/api/calculate/spousal-support",
        json={
            "jurisdiction": "BC",
            "children": 2,
            "taxYear": 2025,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "payorSpousalIncome": 190000,
            "recipientSpousalIncome": 45000,
            "targetMinPercent": 40,
            "targetMaxPercent": 46,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["payorIncome"] == 244658
    assert payload["recipientIncome"] == 30600
    assert payload["payorSpousalIncome"] == 190000
    assert payload["recipientSpousalIncome"] == 45000
    assert payload["childSupport"]["payorIncome"] == 244658
    assert payload["childSupport"]["recipientIncome"] == 30600
    assert payload["ndiChildSupport"]["payorIncome"] == 190000
    assert payload["ndiChildSupport"]["recipientIncome"] == 45000


def test_spousal_support_route_accepts_fixed_total_support(client):
    response = client.post(
        "/api/calculate/spousal-support",
        json={
            "jurisdiction": "BC",
            "children": 2,
            "taxYear": 2025,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "payorSpousalIncome": 190000,
            "recipientSpousalIncome": 45000,
            "fixedTotalSupportAnnual": 50000,
            "targetMinPercent": 40,
            "targetMaxPercent": 46,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["fixedTotalSupportAnnual"] == 50000
    assert payload["iterations"] == 1
    assert payload["ndiChildSupport"] == payload["childSupport"]
    assert payload["estimatedSpousalSupportAnnual"] == approx(
        50000 - payload["childSupport"]["netAnnual"],
        rel=1e-4,
    )


def test_pdf_export_route_returns_pdf(client):
    response = client.post(
        "/api/export/report.pdf",
        json={
            "jurisdiction": "BC",
            "children": 2,
            "childrenUnderSix": 1,
            "taxYear": 2025,
            "payorIncome": 244658,
            "recipientIncome": 30600,
            "targetMinPercent": 40,
            "targetMaxPercent": 46,
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
