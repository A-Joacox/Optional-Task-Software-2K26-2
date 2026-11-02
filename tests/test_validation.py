"""Pruebas unitarias de validación de entradas."""
import pytest
from pydantic import ValidationError

from app.customers import CustomerInput
from app.orders import OrderInput
from app.products import ProductInput


def order(**changes):
    data = {"customer_id": 1, "address": "Calle 10", "city": "Lima", "postal_code": "15001",
            "items": [{"product_id": 1, "quantity": 1}]}
    data.update(changes)
    return OrderInput(**data)


def test_order_defaults_to_standard_shipping_and_strips_text():
    data = order(address="  Calle 10  ")
    assert data.shipping == "standard"
    assert data.address == "Calle 10"


@pytest.mark.parametrize("changes", [
    {"items": []},
    {"items": [{"product_id": 1, "quantity": 0}]},
    {"items": [{"product_id": 1, "quantity": 10_001}]},
    {"items": [{"product_id": 0, "quantity": 1}]},
    {"items": [{"product_id": 1, "quantity": "2"}]},
    {"items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}]},
    {"customer_id": 0},
    {"customer_id": "1"},
    {"shipping": "drone"},
    {"address": "   "},
    {"postal_code": "1" * 21},
    {"coupon": "GRATIS"},
])
def test_invalid_orders_are_rejected(changes):
    with pytest.raises(ValidationError):
        order(**changes)


def test_customer_defaults_to_regular_category():
    assert CustomerInput(name="Ana", email="ana@example.com").category == "regular"


@pytest.mark.parametrize("data", [
    {"name": "Ana", "email": "no-es-correo"},
    {"name": "Ana", "email": "ana@example.com", "category": "vip"},
    {"name": "", "email": "ana@example.com"},
    {"name": "Ana", "email": "ana@example.com", "phone": "999"},
])
def test_invalid_customers_are_rejected(data):
    with pytest.raises(ValidationError):
        CustomerInput(**data)


@pytest.mark.parametrize("data", [
    {"name": "Libro", "price_cents": 0, "stock": 1},
    {"name": "Libro", "price_cents": 100_000_001, "stock": 1},
    {"name": "Libro", "price_cents": 100, "stock": -1},
    {"name": "Libro", "price_cents": "100", "stock": 1},
    {"name": "Libro", "price_cents": 10.5, "stock": 1},
    {"name": " ", "price_cents": 100, "stock": 1},
])
def test_invalid_products_are_rejected(data):
    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_product_accepts_zero_stock():
    assert ProductInput(name="Libro", price_cents=1, stock=0).stock == 0
