from conftest import create_customer, create_product, order_payload


def setup_order(client, stock=5, category="premium"):
    customer = create_customer(client, category=category)
    product = create_product(client, price_cents=2500, stock=stock)
    payload = order_payload(customer["id"], [(product["id"], 2)])
    order = client.post("/orders", json=payload)
    assert order.status_code == 201
    return customer, product, payload, order.json()


def test_quote_matches_created_order(client):
    customer = create_customer(client)
    product = create_product(client)
    payload = order_payload(customer["id"], [(product["id"], 2)])
    quote = client.post("/orders/quote", json=payload)
    assert quote.status_code == 200
    assert quote.json() == {"subtotal_cents": 5000, "discount_cents": 500, "shipping_cents": 1000,
                            "total_cents": 5500}
    order = client.post("/orders", json=payload).json()
    assert {key: order[key] for key in quote.json()} == quote.json()
    assert client.get("/orders").json() != []


def test_orders_list_is_a_summary_and_detail_has_items(client):
    _, product, payload, first = setup_order(client)
    second = client.post("/orders", json=payload).json()
    listing = client.get("/orders").json()
    assert [order["id"] for order in listing] == [first["id"], second["id"]]
    assert "items" not in listing[0]
    detail = client.get(f"/orders/{first['id']}").json()
    assert detail["items"] == [{"product_id": product["id"], "quantity": 2, "unit_price_cents": 2500}]


def test_unknown_customer_or_product_returns_404(client):
    customer = create_customer(client)
    product = create_product(client)
    no_customer = order_payload(99, [(product["id"], 1)])
    no_product = order_payload(customer["id"], [(product["id"], 1), (99, 1)])
    for path in ("/orders", "/orders/quote"):
        assert client.post(path, json=no_customer).json() == {"detail": "Cliente no encontrado"}
        assert client.post(path, json=no_product).json() == {"detail": "Producto 99 no encontrado"}
    assert client.get("/orders").json() == []


def test_missing_order_returns_404(client):
    customer = create_customer(client)
    product = create_product(client)
    payload = order_payload(customer["id"], [(product["id"], 1)])
    assert client.get("/orders/99").json() == {"detail": "Pedido no encontrado"}
    assert client.put("/orders/99", json=payload).status_code == 404
    assert client.delete("/orders/99").status_code == 404
    assert client.post("/orders/99/confirm").status_code == 404
    assert client.post("/orders/99/cancel").status_code == 404
    assert client.get("/orders/99/notifications").status_code == 404


def test_invalid_order_returns_422(client):
    customer = create_customer(client)
    product = create_product(client)
    payload = order_payload(customer["id"], [(product["id"], 0)])
    assert client.post("/orders", json=payload).status_code == 422
    assert client.get("/orders").json() == []


def test_saved_order_keeps_prices_and_category(client):
    customer, product, _, order = setup_order(client)
    client.put(f"/products/{product['id']}", json={"name": "Libro", "price_cents": 9000, "stock": 5})
    client.put(f"/customers/{customer['id']}", json={"name": "Ana", "email": "ana@example.com",
                                                    "category": "regular"})
    stored = client.get(f"/orders/{order['id']}").json()
    assert stored["customer_category"] == "premium"
    assert stored["total_cents"] == 5500
    assert stored["items"][0]["unit_price_cents"] == 2500


def test_put_recalculates_with_current_prices_and_category(client):
    customer, product, payload, order = setup_order(client)
    client.put(f"/products/{product['id']}", json={"name": "Libro", "price_cents": 6000, "stock": 5})
    client.put(f"/customers/{customer['id']}", json={"name": "Ana", "email": "ana@example.com",
                                                    "category": "business"})
    extra = create_product(client, price_cents=1000, name="Agenda")
    payload["items"] = [{"product_id": product["id"], "quantity": 1}, {"product_id": extra["id"], "quantity": 3}]
    payload["shipping"] = "express"
    payload["city"] = "Cusco"

    response = client.put(f"/orders/{order['id']}", json=payload)
    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == order["id"]
    assert updated["status"] == "pending"
    assert updated["city"] == "Cusco"
    assert updated["customer_category"] == "business"
    assert (updated["subtotal_cents"], updated["discount_cents"], updated["shipping_cents"],
            updated["total_cents"]) == (9000, 1350, 2500, 10150)
    assert updated["items"] == [{"product_id": product["id"], "quantity": 1, "unit_price_cents": 6000},
                                {"product_id": extra["id"], "quantity": 3, "unit_price_cents": 1000}]
    assert client.get(f"/orders/{order['id']}").json() == updated


def test_failed_put_leaves_order_unchanged(client):
    _, _, payload, order = setup_order(client)
    payload["items"].append({"product_id": 99, "quantity": 1})
    assert client.put(f"/orders/{order['id']}", json=payload).status_code == 404
    assert client.get(f"/orders/{order['id']}").json() == order


def test_cancel_pending_order(client):
    _, product, _, order = setup_order(client)
    response = client.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 200
    assert response.json() == {"id": order["id"], "status": "cancelled"}
    assert client.get(f"/orders/{order['id']}").json()["status"] == "cancelled"
    assert client.get(f"/products/{product['id']}").json()["stock"] == 5
    assert client.get(f"/orders/{order['id']}/notifications").json() == []


def test_cancelled_order_is_final(client):
    _, product, payload, order = setup_order(client)
    client.post(f"/orders/{order['id']}/cancel")
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409
    assert client.post(f"/orders/{order['id']}/confirm").status_code == 409
    assert client.put(f"/orders/{order['id']}", json=payload).status_code == 409
    assert client.delete(f"/orders/{order['id']}").status_code == 409
    assert client.get(f"/products/{product['id']}").json()["stock"] == 5


def test_confirmed_order_is_final(client):
    _, product, payload, order = setup_order(client)
    confirmed = client.post(f"/orders/{order['id']}/confirm")
    assert confirmed.json() == {"id": order["id"], "status": "confirmed",
                                "message": f"Pedido {order['id']} confirmado. Total: 5500 centavos."}
    assert client.put(f"/orders/{order['id']}", json=payload).json() == {
        "detail": "Solo puede editar pedidos pendientes"}
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409
    assert client.delete(f"/orders/{order['id']}").status_code == 409
    assert client.get(f"/orders/{order['id']}").json()["status"] == "confirmed"
    assert client.get(f"/products/{product['id']}").json()["stock"] == 3


def test_notification_goes_to_customer_email(client):
    customer, _, _, order = setup_order(client)
    client.post(f"/orders/{order['id']}/confirm")
    notifications = client.get(f"/orders/{order['id']}/notifications").json()
    assert notifications == [{"id": notifications[0]["id"], "order_id": order["id"],
                              "recipient": customer["email"],
                              "message": f"Pedido {order['id']} confirmado. Total: 5500 centavos."}]


def test_confirm_can_use_all_remaining_stock(client):
    _, product, _, order = setup_order(client, stock=2)
    assert client.post(f"/orders/{order['id']}/confirm").status_code == 200
    assert client.get(f"/products/{product['id']}").json()["stock"] == 0


def test_insufficient_stock_on_single_line(client):
    _, product, _, order = setup_order(client, stock=1)
    response = client.post(f"/orders/{order['id']}/confirm")
    assert response.json() == {"detail": f"Stock insuficiente para producto {product['id']}"}
    assert client.get(f"/products/{product['id']}").json()["stock"] == 1
    assert client.get(f"/orders/{order['id']}").json()["status"] == "pending"


def test_delete_pending_order_removes_its_lines(client):
    customer, product, _, order = setup_order(client)
    response = client.delete(f"/orders/{order['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/orders/{order['id']}").status_code == 404
    assert client.get("/orders").json() == []
    assert client.delete(f"/products/{product['id']}").status_code == 204
    assert client.delete(f"/customers/{customer['id']}").status_code == 204
