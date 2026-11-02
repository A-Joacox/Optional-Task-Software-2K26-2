from conftest import create_customer, create_product, order_payload


def test_customer_crud(client):
    customer = create_customer(client, email="ana@example.com", category="premium")
    assert customer == {"id": customer["id"], "name": "Ana", "email": "ana@example.com", "category": "premium"}
    assert client.get(f"/customers/{customer['id']}").json() == customer

    body = {"name": "Ana Torres", "email": "ana.torres@example.com", "category": "business"}
    updated = client.put(f"/customers/{customer['id']}", json=body)
    assert updated.status_code == 200
    assert updated.json() == {"id": customer["id"], **body}

    assert client.delete(f"/customers/{customer['id']}").status_code == 204
    assert client.get(f"/customers/{customer['id']}").status_code == 404


def test_customer_category_defaults_to_regular(client):
    response = client.post("/customers", json={"name": "Luis", "email": "luis@example.com"})
    assert response.json()["category"] == "regular"


def test_customers_are_listed_by_id(client):
    first = create_customer(client, email="a@example.com")
    second = create_customer(client, email="b@example.com")
    assert [customer["id"] for customer in client.get("/customers").json()] == [first["id"], second["id"]]


def test_email_must_be_unique(client):
    create_customer(client, email="ana@example.com")
    other = create_customer(client, email="luis@example.com")
    duplicate = client.post("/customers", json={"name": "Otra", "email": "ana@example.com"})
    assert duplicate.status_code == 409
    update = client.put(f"/customers/{other['id']}", json={"name": "Luis", "email": "ana@example.com"})
    assert update.status_code == 409
    assert client.get(f"/customers/{other['id']}").json()["email"] == "luis@example.com"
    assert len(client.get("/customers").json()) == 2


def test_missing_customer_returns_404(client):
    body = {"name": "Ana", "email": "ana@example.com"}
    assert client.get("/customers/99").json() == {"detail": "Cliente no encontrado"}
    assert client.put("/customers/99", json=body).status_code == 404
    assert client.delete("/customers/99").status_code == 404


def test_invalid_customer_returns_422(client):
    assert client.post("/customers", json={"name": "Ana", "email": "no-es-correo"}).status_code == 422
    assert client.get("/customers").json() == []


def test_customer_with_orders_cannot_be_deleted(client):
    customer = create_customer(client)
    product = create_product(client)
    client.post("/orders", json=order_payload(customer["id"], [(product["id"], 1)]))
    response = client.delete(f"/customers/{customer['id']}")
    assert response.status_code == 409
    assert client.get(f"/customers/{customer['id']}").status_code == 200
