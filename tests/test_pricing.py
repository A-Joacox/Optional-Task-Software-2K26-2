"""Pruebas unitarias de las reglas de precio: usan OrderService y la base directamente, sin HTTP."""
from typing import get_args

import pytest
from fastapi import HTTPException

from app.customers import CustomerInput
from app.orders import DISCOUNT_PERCENT, OrderInput, OrderService, calculate_totals


def insert_customer(database, category):
    with database.connect() as connection:
        return connection.execute(
            "INSERT INTO customers(name, email, category) VALUES (?, ?, ?)",
            ("Ana", f"{category}@example.com", category),
        ).lastrowid


def insert_product(database, price_cents, stock=10):
    with database.connect() as connection:
        return connection.execute(
            "INSERT INTO products(name, price_cents, stock) VALUES (?, ?, ?)", ("Producto", price_cents, stock),
        ).lastrowid


def quote(database, category, lines, shipping="standard"):
    customer_id = insert_customer(database, category)
    items = [{"product_id": insert_product(database, price), "quantity": quantity} for price, quantity in lines]
    data = OrderInput(customer_id=customer_id, address="Calle 10", city="Lima", postal_code="15001",
                      shipping=shipping, items=items)
    return OrderService(database).quote(data)


@pytest.mark.parametrize(("category", "discount"), [("regular", 0), ("premium", 500), ("business", 750)])
def test_discount_depends_on_customer_category(database, category, discount):
    result = quote(database, category, [(2500, 2)], shipping="pickup")
    assert result == {"subtotal_cents": 5000, "discount_cents": discount, "shipping_cents": 0,
                      "total_cents": 5000 - discount}


@pytest.mark.parametrize(("category", "discount"), [("premium", 99), ("business", 149)])
def test_discount_is_truncated_to_whole_cents(database, category, discount):
    result = quote(database, category, [(999, 1)], shipping="pickup")
    assert result["discount_cents"] == discount
    assert result["total_cents"] == 999 - discount


@pytest.mark.parametrize(("shipping", "subtotal", "delivery"), [
    ("pickup", 5000, 0),
    ("standard", 9999, 1000),
    ("standard", 10000, 0),
    ("express", 5000, 2500),
    ("express", 20000, 2500),
])
def test_shipping_cost(database, shipping, subtotal, delivery):
    result = quote(database, "regular", [(subtotal, 1)], shipping=shipping)
    assert result["shipping_cents"] == delivery
    assert result["total_cents"] == subtotal + delivery


def test_free_shipping_threshold_uses_subtotal_before_discount(database):
    result = quote(database, "business", [(10000, 1)])
    assert result == {"subtotal_cents": 10000, "discount_cents": 1500, "shipping_cents": 0, "total_cents": 8500}


def test_subtotal_adds_every_line(database):
    result = quote(database, "regular", [(2500, 2), (1200, 3)], shipping="pickup")
    assert result["subtotal_cents"] == 8600


def test_quote_does_not_reserve_stock(database):
    customer_id = insert_customer(database, "regular")
    product_id = insert_product(database, 2500, stock=1)
    data = OrderInput(customer_id=customer_id, address="Calle 10", city="Lima", postal_code="15001",
                      items=[{"product_id": product_id, "quantity": 5}])
    assert OrderService(database).quote(data)["subtotal_cents"] == 12500
    with database.connect() as connection:
        assert connection.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()[0] == 1


def test_saved_order_stores_the_same_totals_as_the_quote(database):
    customer_id = insert_customer(database, "premium")
    product_id = insert_product(database, 2500)
    data = OrderInput(customer_id=customer_id, address="Calle 10", city="Lima", postal_code="15001",
                      shipping="express", items=[{"product_id": product_id, "quantity": 2}])
    order = OrderService(database).create(data)
    assert order["status"] == "pending"
    assert order["customer_category"] == "premium"
    assert (order["subtotal_cents"], order["discount_cents"], order["shipping_cents"], order["total_cents"]) == (
        5000, 500, 2500, 7000)
    assert order["items"] == [{"product_id": product_id, "quantity": 2, "unit_price_cents": 2500}]


@pytest.mark.parametrize("category", ["regular", "premium", "business"])
@pytest.mark.parametrize("shipping", ["pickup", "standard", "express"])
@pytest.mark.parametrize("unit_price", [3333, 6000])
def test_create_and_quote_apply_the_same_rules(database, category, shipping, unit_price):
    customer_id = insert_customer(database, category)
    product_id = insert_product(database, unit_price)
    data = OrderInput(customer_id=customer_id, address="Calle 10", city="Lima", postal_code="15001",
                      shipping=shipping, items=[{"product_id": product_id, "quantity": 2}])
    service = OrderService(database)
    quoted = service.quote(data)
    saved = service.create(data)
    assert {key: saved[key] for key in quoted} == quoted


@pytest.mark.parametrize(("category", "shipping", "subtotal", "expected"), [
    ("regular", "standard", 9999, (0, 1000, 10999)),
    ("premium", "standard", 10000, (1000, 0, 9000)),
    ("business", "express", 999, (149, 2500, 3350)),
    ("premium", "pickup", 999, (99, 0, 900)),
])
def test_calculate_totals_without_database(category, shipping, subtotal, expected):
    assert calculate_totals(category, shipping, subtotal) == {
        "subtotal_cents": subtotal, "discount_cents": expected[0], "shipping_cents": expected[1],
        "total_cents": expected[2]}


def test_every_customer_category_has_a_discount():
    categories = get_args(CustomerInput.model_fields["category"].annotation)
    assert set(DISCOUNT_PERCENT) == set(categories)


def test_quote_rejects_unknown_customer_and_product(database):
    data = OrderInput(customer_id=99, address="Calle 10", city="Lima", postal_code="15001",
                      items=[{"product_id": 1, "quantity": 1}])
    with pytest.raises(HTTPException) as error:
        OrderService(database).quote(data)
    assert error.value.status_code == 404

    data.customer_id = insert_customer(database, "regular")
    with pytest.raises(HTTPException) as error:
        OrderService(database).quote(data)
    assert error.value.status_code == 404
    assert error.value.detail == "Producto 1 no encontrado"
