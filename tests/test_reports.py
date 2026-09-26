def test_reports_require_login(client):
    assert client.get("/reports/summary").status_code == 401
    assert client.get("/reports/monthly").status_code == 401
    assert client.get("/reports/export.csv").status_code == 401


def test_summary(client, auth_headers, make_expense):
    make_expense(category="food", amount=10)
    make_expense(category="food", amount=5.5)
    make_expense(category="transport", amount=20)

    response = client.get("/reports/summary", headers=auth_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["total"] == 35.5
    assert summary["count"] == 3
    # Biggest category comes first
    assert summary["by_category"][0] == {"category": "transport", "total": 20.0, "count": 1}
    assert summary["by_category"][1] == {"category": "food", "total": 15.5, "count": 2}


def test_summary_when_empty(client, auth_headers):
    response = client.get("/reports/summary", headers=auth_headers)
    assert response.json() == {"total": 0, "count": 0, "by_category": []}


def test_summary_with_date_range(client, auth_headers, make_expense):
    make_expense(category="food", amount=10, spent_on="2026-08-15")      # outside
    make_expense(category="food", amount=5, spent_on="2026-09-05")       # inside
    make_expense(category="transport", amount=20, spent_on="2026-09-06") # inside

    response = client.get(
        "/reports/summary",
        params={"start_date": "2026-09-01", "end_date": "2026-09-30"},
        headers=auth_headers,
    )
    summary = response.json()
    assert summary["total"] == 25
    assert summary["count"] == 2


def test_monthly_totals_are_sorted_by_month(client, auth_headers, make_expense):
    make_expense(amount=10, spent_on="2026-08-10")
    make_expense(amount=5, spent_on="2026-09-01")
    make_expense(amount=7.5, spent_on="2026-09-20")
    make_expense(amount=3, spent_on="2025-12-31")

    data = client.get("/reports/monthly", headers=auth_headers).json()
    assert [m["month"] for m in data] == ["2025-12", "2026-08", "2026-09"]
    assert data[2] == {"month": "2026-09", "total": 12.5, "count": 2}


def test_monthly_totals_filtered_by_year(client, auth_headers, make_expense):
    make_expense(spent_on="2025-12-31")
    make_expense(spent_on="2026-01-01")
    make_expense(spent_on="2026-05-10")

    data = client.get("/reports/monthly", params={"year": 2026}, headers=auth_headers).json()
    assert [m["month"] for m in data] == ["2026-01", "2026-05"]


def test_monthly_rejects_invalid_year(client, auth_headers):
    response = client.get("/reports/monthly", params={"year": 1500}, headers=auth_headers)
    assert response.status_code == 422


def test_export_csv(client, auth_headers, make_expense):
    make_expense(title="Taxi", category="transport")
    make_expense(title="Dinner", category="food")

    response = client.get("/reports/export.csv", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip().splitlines()
    assert lines[0] == "id,title,amount,category,spent_on,note"
    assert len(lines) == 3


def test_export_csv_only_contains_own_expenses(client, register_and_login, make_expense):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    make_expense(headers=alice, title="Taxi")
    make_expense(headers=bob, title="Secret")

    text = client.get("/reports/export.csv", headers=alice).text
    assert "Taxi" in text
    assert "Secret" not in text