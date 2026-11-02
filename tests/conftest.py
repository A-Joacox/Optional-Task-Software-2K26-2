import pytest
from fastapi.testclient import TestClient

from app.database import Database
from main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3")) as session:
        yield session


@pytest.fixture
def database(tmp_path):
    database = Database(tmp_path / "unit.sqlite3")
    database.initialize()
    return database


def create_customer(client, email="ana@example.com", category="premium", name="Ana"):
    response = client.post("/customers", json={"name": name, "email": email, "category": category})
    assert response.status_code == 201
    return response.json()


def create_product(client, price_cents=2500, stock=5, name="Libro"):
    response = client.post("/products", json={"name": name, "price_cents": price_cents, "stock": stock})
    assert response.status_code == 201
    return response.json()


def order_payload(customer_id, items, shipping="standard"):
    return {"customer_id": customer_id, "address": "Calle 10", "city": "Lima", "postal_code": "15001",
            "shipping": shipping, "items": [{"product_id": product_id, "quantity": quantity}
                                            for product_id, quantity in items]}
