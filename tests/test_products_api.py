from conftest import create_customer, create_product, order_payload


def test_product_crud(client):
    product = create_product(client, name="Libro", price_cents=2500, stock=5)
    assert product == {"id": product["id"], "name": "Libro", "price_cents": 2500, "stock": 5}
    assert client.get(f"/products/{product['id']}").json() == product

    updated = client.put(f"/products/{product['id']}", json={"name": "Libro 2", "price_cents": 3000, "stock": 1})
    assert updated.status_code == 200
    assert updated.json() == {"id": product["id"], "name": "Libro 2", "price_cents": 3000, "stock": 1}
    assert client.get(f"/products/{product['id']}").json()["price_cents"] == 3000

    deleted = client.delete(f"/products/{product['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/products/{product['id']}").status_code == 404


def test_products_are_listed_by_id(client):
    first = create_product(client, name="A")
    second = create_product(client, name="B")
    assert [product["id"] for product in client.get("/products").json()] == [first["id"], second["id"]]


def test_missing_product_returns_404(client):
    body = {"name": "Libro", "price_cents": 100, "stock": 1}
    assert client.get("/products/99").json() == {"detail": "Producto no encontrado"}
    assert client.put("/products/99", json=body).status_code == 404
    assert client.delete("/products/99").status_code == 404


def test_invalid_product_returns_422_and_is_not_saved(client):
    assert client.post("/products", json={"name": "Libro", "price_cents": 0, "stock": 1}).status_code == 422
    assert client.get("/products").json() == []


def test_product_in_an_order_cannot_be_deleted(client):
    customer = create_customer(client)
    product = create_product(client)
    client.post("/orders", json=order_payload(customer["id"], [(product["id"], 1)]))
    response = client.delete(f"/products/{product['id']}")
    assert response.status_code == 409
    assert client.get(f"/products/{product['id']}").status_code == 200
