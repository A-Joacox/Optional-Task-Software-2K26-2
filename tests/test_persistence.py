import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.database import Database
from main import create_app
from conftest import create_customer, create_product


def count_products(database):
    with database.connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]


def test_initialize_creates_missing_folder_and_is_repeatable(tmp_path):
    database = Database(tmp_path / "nested" / "folder" / "store.sqlite3")
    database.initialize()
    database.initialize()
    assert (tmp_path / "nested" / "folder" / "store.sqlite3").exists()
    assert count_products(database) == 0


def test_connect_commits_on_success(database):
    with database.connect() as connection:
        connection.execute("INSERT INTO products(name, price_cents, stock) VALUES ('Libro', 100, 1)")
    assert count_products(database) == 1


def test_connect_rolls_back_on_error(database):
    with pytest.raises(RuntimeError):
        with database.connect() as connection:
            connection.execute("INSERT INTO products(name, price_cents, stock) VALUES ('Libro', 100, 1)")
            raise RuntimeError("falla a mitad de la transacción")
    assert count_products(database) == 0


def test_foreign_keys_are_enforced(database):
    with pytest.raises(sqlite3.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """INSERT INTO orders(customer_id, customer_category, address, city, postal_code, shipping,
                   subtotal_cents, discount_cents, shipping_cents, total_cents)
                   VALUES (99, 'regular', 'Calle', 'Lima', '1', 'pickup', 1, 0, 0, 1)""")


def test_data_survives_restart(tmp_path):
    path = tmp_path / "store.sqlite3"
    with TestClient(create_app(path)) as client:
        customer = create_customer(client)
        product = create_product(client, stock=7)
    with TestClient(create_app(path)) as client:
        assert client.get(f"/customers/{customer['id']}").json() == customer
        assert client.get(f"/products/{product['id']}").json()["stock"] == 7


def test_database_path_comes_from_environment(tmp_path, monkeypatch):
    path = tmp_path / "from-env.sqlite3"
    monkeypatch.setenv("LAB_DB_PATH", str(path))
    application = create_app()
    assert application.state.database.path == str(path)
    with TestClient(application) as client:
        create_product(client)
    assert path.exists()


def test_unavailable_database_returns_503(tmp_path):
    path = tmp_path / "store.sqlite3"
    with TestClient(create_app(path)) as client:
        os.remove(path)
        os.mkdir(path)
        response = client.get("/products")
    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible; reintente más tarde"}
