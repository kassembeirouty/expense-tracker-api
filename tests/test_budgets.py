def create_budget(client, headers, category="food", month="2026-09", limit_amount=100):
    response = client.post(
        "/budgets",
        json={"category": category, "month": month, "limit_amount": limit_amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_budgets_require_login(client):
    assert client.get("/budgets").status_code == 401


def test_create_budget(client, auth_headers):
    budget = create_budget(client, auth_headers)
    assert budget["id"] == 1
    assert budget["category"] == "food"
    assert budget["month"] == "2026-09"
    assert budget["limit_amount"] == 100


def test_duplicate_budget_is_rejected(client, auth_headers):
    create_budget(client, auth_headers)
    response = client.post(
        "/budgets",
        json={"category": "food", "month": "2026-09", "limit_amount": 200},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_invalid_month_format_is_rejected(client, auth_headers):
    for bad_month in ["2026-13", "2026-9", "09-2026", "2026/09"]:
        response = client.post(
            "/budgets",
            json={"category": "food", "month": bad_month, "limit_amount": 100},
            headers=auth_headers,
        )
        assert response.status_code == 422, bad_month


def test_budget_status_counts_only_same_category_and_month(
    client, auth_headers, make_expense
):
    budget = create_budget(client, auth_headers, limit_amount=100)

    make_expense(category="food", amount=40, spent_on="2026-09-05")       # counted
    make_expense(category="food", amount=30, spent_on="2026-09-30")       # counted
    make_expense(category="food", amount=50, spent_on="2026-10-01")       # other month
    make_expense(category="transport", amount=25, spent_on="2026-09-10")  # other category

    status = client.get(f"/budgets/{budget['id']}", headers=auth_headers).json()
    assert status["spent"] == 70
    assert status["remaining"] == 30
    assert status["percent_used"] == 70.0
    assert status["over_budget"] is False


def test_budget_status_when_over_budget(client, auth_headers, make_expense):
    budget = create_budget(client, auth_headers, limit_amount=50)
    make_expense(category="food", amount=70, spent_on="2026-09-15")

    status = client.get(f"/budgets/{budget['id']}", headers=auth_headers).json()
    assert status["spent"] == 70
    assert status["remaining"] == -20
    assert status["percent_used"] == 140.0
    assert status["over_budget"] is True


def test_december_budget_handles_year_change(client, auth_headers, make_expense):
    budget = create_budget(client, auth_headers, month="2026-12", limit_amount=100)
    make_expense(category="food", amount=10, spent_on="2026-12-31")  # counted
    make_expense(category="food", amount=99, spent_on="2027-01-01")  # next year

    status = client.get(f"/budgets/{budget['id']}", headers=auth_headers).json()
    assert status["spent"] == 10


def test_list_budgets_filtered_by_month(client, auth_headers):
    create_budget(client, auth_headers, category="food", month="2026-09")
    create_budget(client, auth_headers, category="transport", month="2026-09")
    create_budget(client, auth_headers, category="food", month="2026-10")

    response = client.get("/budgets", params={"month": "2026-09"}, headers=auth_headers)
    data = response.json()
    assert len(data) == 2
    assert {b["category"] for b in data} == {"food", "transport"}


def test_update_budget_limit(client, auth_headers):
    budget = create_budget(client, auth_headers, limit_amount=100)

    response = client.patch(
        f"/budgets/{budget['id']}", json={"limit_amount": 250}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["limit_amount"] == 250


def test_delete_budget(client, auth_headers):
    budget = create_budget(client, auth_headers)

    assert client.delete(f"/budgets/{budget['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/budgets/{budget['id']}", headers=auth_headers).status_code == 404


# ---------- Data isolation between users ----------

def test_users_cannot_access_each_others_budgets(client, register_and_login):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    budget = create_budget(client, alice)
    url = f"/budgets/{budget['id']}"

    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"limit_amount": 1}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    assert client.get("/budgets", headers=bob).json() == []


def test_two_users_can_have_same_category_and_month(client, register_and_login):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    create_budget(client, alice, category="food", month="2026-09")
    create_budget(client, bob, category="food", month="2026-09")  # must not conflict


def test_other_users_expenses_do_not_count_in_budget(
    client, register_and_login, make_expense
):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    budget = create_budget(client, alice, limit_amount=100)
    make_expense(headers=alice, category="food", amount=20, spent_on="2026-09-10")
    make_expense(headers=bob, category="food", amount=500, spent_on="2026-09-10")

    status = client.get(f"/budgets/{budget['id']}", headers=alice).json()
    assert status["spent"] == 20