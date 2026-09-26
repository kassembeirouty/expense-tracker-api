def test_expenses_require_login(client):
    assert client.get("/expenses").status_code == 401
    assert client.post("/expenses", json={}).status_code == 401


def test_create_expense(make_expense):
    expense = make_expense(title="Coffee", amount=3.5, note="morning")
    assert expense["id"] == 1
    assert expense["title"] == "Coffee"
    assert expense["amount"] == 3.5
    assert expense["note"] == "morning"
    assert "created_at" in expense


def test_create_expense_rejects_negative_amount(client, auth_headers):
    response = client.post(
        "/expenses",
        json={"title": "Bad", "amount": -5, "category": "food", "spent_on": "2026-09-01"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_expense_rejects_unknown_category(client, auth_headers):
    response = client.post(
        "/expenses",
        json={"title": "Bad", "amount": 5, "category": "gambling", "spent_on": "2026-09-01"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_get_missing_expense_returns_404(client, auth_headers):
    response = client.get("/expenses/999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Expense not found"


def test_list_filters_by_category(client, auth_headers, make_expense):
    make_expense(category="food")
    make_expense(category="transport")
    make_expense(category="food")

    response = client.get("/expenses", params={"category": "food"}, headers=auth_headers)
    data = response.json()
    assert len(data) == 2
    assert all(e["category"] == "food" for e in data)


def test_list_filters_by_date_range(client, auth_headers, make_expense):
    make_expense(spent_on="2026-08-15")
    make_expense(spent_on="2026-09-05")
    make_expense(spent_on="2026-09-20")

    response = client.get(
        "/expenses",
        params={"start_date": "2026-09-01", "end_date": "2026-09-10"},
        headers=auth_headers,
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["spent_on"] == "2026-09-05"


def test_list_rejects_reversed_dates(client, auth_headers):
    response = client.get(
        "/expenses",
        params={"start_date": "2026-09-30", "end_date": "2026-09-01"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_list_is_sorted_newest_first(client, auth_headers, make_expense):
    make_expense(title="Old", spent_on="2026-01-01")
    make_expense(title="New", spent_on="2026-09-01")

    data = client.get("/expenses", headers=auth_headers).json()
    assert [e["title"] for e in data] == ["New", "Old"]


def test_list_pagination(client, auth_headers, make_expense):
    for i in range(5):
        make_expense(title=f"Item {i}")

    response = client.get("/expenses", params={"skip": 2, "limit": 2}, headers=auth_headers)
    assert len(response.json()) == 2


def test_update_expense_partially(client, auth_headers, make_expense):
    expense = make_expense(title="Old title", amount=20)

    response = client.patch(
        f"/expenses/{expense['id']}", json={"title": "New title"}, headers=auth_headers
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "New title"
    assert updated["amount"] == 20  # unchanged


def test_update_can_clear_note(client, auth_headers, make_expense):
    expense = make_expense(note="temporary")

    response = client.patch(
        f"/expenses/{expense['id']}", json={"note": None}, headers=auth_headers
    )
    assert response.json()["note"] is None


def test_delete_expense(client, auth_headers, make_expense):
    expense = make_expense()

    response = client.delete(f"/expenses/{expense['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/expenses/{expense['id']}", headers=auth_headers)
    assert response.status_code == 404


# ---------- Data isolation between users ----------

def test_users_only_see_their_own_expenses(client, register_and_login, make_expense):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    make_expense(headers=alice, title="Alice lunch")
    make_expense(headers=bob, title="Bob taxi")

    alice_list = client.get("/expenses", headers=alice).json()
    bob_list = client.get("/expenses", headers=bob).json()

    assert [e["title"] for e in alice_list] == ["Alice lunch"]
    assert [e["title"] for e in bob_list] == ["Bob taxi"]


def test_user_cannot_read_update_or_delete_another_users_expense(
    client, register_and_login, make_expense
):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")

    expense = make_expense(headers=alice, title="Private")
    url = f"/expenses/{expense['id']}"

    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"title": "Hacked"}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404

    # Alice's expense is untouched
    response = client.get(url, headers=alice)
    assert response.status_code == 200
    assert response.json()["title"] == "Private"