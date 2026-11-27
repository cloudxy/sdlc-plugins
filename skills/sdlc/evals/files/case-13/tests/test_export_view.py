def test_export_returns_csv(client, admin_user):
    client.force_login(admin_user)
    response = client.get("/orders/export?date=2026-09")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
