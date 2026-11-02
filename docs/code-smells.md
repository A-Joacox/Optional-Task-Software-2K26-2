# 4. Code smells

Código analizado: revisión inicial `969cbdb`. Las líneas corresponden a esa revisión. La clasificación sigue el catálogo de Fowler (*Refactoring*, 2.ª ed.) y sus categorías habituales: Bloaters, Dispensables, Change Preventers, Couplers y Object-Orientation Abusers.

SonarQube no reportó ninguno de estos smells (0 issues con *Sonar way core*, ver [evidencias/sonarqube.md](evidencias/sonarqube.md)). Todos salen de la revisión manual del código.

| # | Smell | Categoría | Ubicación principal |
| --- | --- | --- | --- |
| 1 | Duplicated Code | Dispensables | `OrderService.save` y `OrderService.quote` |
| 2 | Long Method | Bloaters | `OrderService.save` |
| 3 | Long Parameter List con Flag Argument | Bloaters | Firma de `OrderService.save` y sus llamadas |
| 4 | Primitive Obsession | Bloaters | Categorías, envíos, estados e importes como literales |
| 5 | Divergent Change | Change Preventers | `OrderService` completo |

---

## 1. Duplicated Code

- **Categoría:** Dispensables.
- **Ubicación:** `app/orders.py`, clase `OrderService`. `save`, líneas 41-64, y `quote`, líneas 94-116.

Las dos funciones repiten la búsqueda del cliente y los productos, el cálculo del subtotal, el descuento y el envío:

```python
# save (líneas 52-64)
            if customer["category"] == "premium":
                discount = subtotal * 10 // 100
            elif customer["category"] == "business":
                discount = subtotal * 15 // 100
            else:
                discount = 0
            if shipping == "pickup":
                delivery = 0
            elif shipping == "standard":
                delivery = 0 if subtotal >= 10_000 else 1_000
            else:
                delivery = 2_500
            total = subtotal - discount + delivery

# quote (líneas 103-116)
            if customer["category"] == "premium":
                discount = subtotal * 10 // 100
            elif customer["category"] == "business":
                discount = subtotal * 15 // 100
            else:
                discount = 0
            if data.shipping == "pickup":
                delivery = 0
            elif data.shipping == "standard":
                delivery = 0 if subtotal >= 10_000 else 1_000
            else:
                delivery = 2_500
            return {"subtotal_cents": subtotal, "discount_cents": discount,
                    "shipping_cents": delivery, "total_cents": subtotal - discount + delivery}
```

La misma duplicación aparece en otro lugar. La secuencia "buscar el pedido, responder 404 si no existe, responder 409 si no está pendiente" se repite cuatro veces: `save` 36-40, `confirm` 136-140, `cancel` 160-164 y `delete` 170-174.

**Problema de mantenimiento.** Las reglas de precio no tienen un único dueño. Cualquier cambio en una regla de negocio exige editar dos bloques casi idénticos. Si se olvida uno, la cotización deja de coincidir con el pedido guardado y no hay ningún error que lo avise.

**Cambio que lo hace evidente.** Subir el umbral de envío gratis de 10000 a 15000. Se probó en una copia del código, cambiando solo la línea 112 (`quote`). Un pedido con subtotal 12000 se cotiza con envío 1000, pero al crearlo se guarda con envío 0. Ninguna prueba HTTP lo detectó; solo fallaron las pruebas unitarias de cotización y la prueba que compara `save` con `quote` (`test_save_and_quote_apply_the_same_rules`, 3 casos con envío standard).

SonarQube tampoco lo marca como duplicación (0,0 %), porque los bloques no son idénticos token por token: `shipping` frente a `data.shipping`, y `save` intercala `lines.append(...)`.

---

## 2. Long Method

- **Categoría:** Bloaters.
- **Ubicación:** `app/orders.py`, `OrderService.save`, líneas 33-90 (58 líneas).

Un solo método, dentro de una sola transacción, hace ocho cosas distintas:

| Líneas | Responsabilidad |
| --- | --- |
| 35-40 | Si es una edición, verificar que el pedido exista y esté pendiente |
| 41-43 | Cargar el cliente |
| 44-51 | Cargar los productos, calcular el subtotal y preparar las líneas |
| 52-57 | Calcular el descuento por categoría |
| 58-63 | Calcular el envío |
| 64-80 | Calcular el total e insertar o actualizar el pedido |
| 81-84 | Insertar las líneas del pedido |
| 85-90 | Releer el pedido y armar la respuesta |

```python
    def save(self, customer_id, address, city, postal_code, shipping, items, order_id=None):
        with self.database.connect() as connection:
            if order_id is not None:
                old = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
                ...
            customer = connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
            ...
            subtotal = 0
            lines = []
            for item in items:
                ...
            if customer["category"] == "premium":
                ...
            if order_id is None:
                cursor = connection.execute("""INSERT INTO orders(...) ...""", values)
                order_id = cursor.lastrowid
            else:
                connection.execute("""UPDATE orders SET ... WHERE id = ?""", (*values, order_id))
                connection.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            ...
            return result
```

**Problema de mantenimiento.** El cálculo de precios no tiene nombre ni frontera propia: vive en medio del acceso a datos. Para entender o cambiar una regla hay que leer el método entero, y no se puede probar el cálculo sin una base de datos. Las pruebas unitarias de `tests/test_pricing.py` tienen que insertar clientes y productos en SQLite solo para verificar una multiplicación.

**Cambio que lo hace evidente.** Agregar un impuesto o un recargo por ciudad. El cambio cae entre la línea 63 y la 64, en medio de un método que además lee y escribe cinco tablas, y obliga a revisar que `values` (65-66), el `INSERT` (69-71), el `UPDATE` (76-78) y la respuesta sigan alineados.

---

## 3. Long Parameter List con Flag Argument

- **Categoría:** Bloaters.
- **Ubicación:** `app/orders.py`. La firma de `OrderService.save` está en la línea 33; las llamadas, en `create_order` (195-197) y `update_order` (212-214).

```python
    def save(self, customer_id, address, city, postal_code, shipping, items, order_id=None):   # línea 33

# create_order (líneas 195-197)
    return OrderService(request.app.state.database).save(
        data.customer_id, data.address, data.city, data.postal_code, data.shipping, data.items,
    )

# update_order (líneas 212-214)
    return OrderService(request.app.state.database).save(
        data.customer_id, data.address, data.city, data.postal_code, data.shipping, data.items, order_id,
    )
```

`save` recibe siete parámetros sueltos. Las rutas ya tienen un objeto `OrderInput` que los agrupa, pero lo desarman campo por campo y los pasan por posición. Además, `order_id=None` funciona como bandera: decide si el método crea o edita (líneas 35, 67 y 74), así que una misma función tiene dos comportamientos. `address`, `city` y `postal_code` también forman un *data clump*: viajan siempre juntos por `OrderInput`, la firma, la tupla `values` y las columnas SQL.

**Problema de mantenimiento.** Como los parámetros son posicionales y varios son `str`, intercambiar dos de ellos (por ejemplo `city` y `postal_code`) no produce ningún error: el pedido se guarda con los datos cruzados. La bandera obliga a quien lee el código a seguir dos caminos dentro del mismo método. Y crear y editar no se pueden cambiar de forma independiente.

**Cambio que lo hace evidente.** Agregar un campo `phone` o `notes` al pedido. Hay que editar `OrderInput`, la firma de `save`, las dos llamadas, la tupla `values` y las dos sentencias SQL: siete lugares para un solo dato, sin contar el esquema de la tabla.

---

## 4. Primitive Obsession

- **Categoría:** Bloaters.
- **Ubicación:** `app/orders.py` y `app/customers.py`.

Los conceptos del dominio se representan con cadenas y números sueltos:

| Concepto | Dónde aparece (líneas de `app/orders.py`, salvo indicación) |
| --- | --- |
| Categoría de cliente | `"premium"`, `"business"` en 52, 54, 103, 105; `Literal[...]` en `app/customers.py:12` |
| Tipo de envío | `Literal[...]` en 19; `"pickup"`, `"standard"` en 58, 60, 109, 111 |
| Estado del pedido | `"pending"` en 39, 139, 163, 173; `'confirmed'` en 155-156; `'cancelled'` en 165-166; `DEFAULT 'pending'` en `app/database.py` |
| Porcentajes e importes | `10`, `15` (53-55, 104-106); `10_000`, `1_000` (61, 112); `2_500` (63, 114) |

```python
# app/customers.py, línea 12
    category: Literal["regular", "premium", "business"] = "regular"

# app/orders.py, líneas 52-57
            if customer["category"] == "premium":
                discount = subtotal * 10 // 100
            elif customer["category"] == "business":
                discount = subtotal * 15 // 100
            else:
                discount = 0
```

**Problema de mantenimiento.** Una categoría no sabe cuál es su descuento: ese conocimiento está repartido en comparaciones de texto, en dos archivos. La rama `else: discount = 0` hace que cualquier valor que no coincida exactamente reciba 0 % de descuento sin ningún aviso. Las transiciones de estado también dependen de comparar cadenas escritas a mano en cada método.

**Cambio que lo hace evidente.** Agregar una categoría `vip` con 20 % de descuento. Si se añade a `Literal` en `app/customers.py`, la API acepta clientes `vip`, pero `OrderService` los manda a la rama `else` y les cobra el precio completo, sin errores. Para hacerlo bien hay que encontrar y editar las dos cadenas `if/elif` de `app/orders.py`. Lo mismo pasa con una errata como `"premuim"` en una sola de las comparaciones.

---

## 5. Divergent Change

- **Categoría:** Change Preventers.
- **Ubicación:** `app/orders.py`, clase `OrderService`, líneas 29-182.

`OrderService` cambia por motivos que no tienen relación entre sí:

| Motivo de cambio | Dónde |
| --- | --- |
| Reglas de precio | `save` 52-64, `quote` 103-116 |
| Esquema y SQL de cinco tablas, incluidas las de otros módulos | `customers` en 41, 94, 149; `products` en 47, 99, 143-146 (descuenta stock directamente); `orders`, `order_items`, `notifications` |
| Contrato HTTP | `from fastapi import HTTPException` y 14 `raise HTTPException(código, mensaje)` dentro del servicio |
| Notificaciones | `confirm` 149-154: arma el mensaje y lo inserta dentro de la transacción del stock |

```python
    def confirm(self, order_id):
        with self.database.connect() as connection:
            ...
                cursor = connection.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?", ...)
                if cursor.rowcount == 0:
                    raise HTTPException(409, f"Stock insuficiente para producto {item['product_id']}")
            customer = connection.execute("SELECT * FROM customers WHERE id = ?", (order["customer_id"],)).fetchone()
            message = f"Pedido {order_id} confirmado. Total: {order['total_cents']} centavos."
            connection.execute("INSERT INTO notifications(order_id, recipient, message) VALUES (?, ?, ?)", ...)
            connection.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order_id,))
```

El módulo de pedidos también conoce el esquema interno de `products` y `customers` y los modifica con SQL propio, saltándose sus módulos. Es un *Insider Trading* entre cortes verticales que, en teoría, son independientes.

**Problema de mantenimiento.** Cambios de equipos o áreas distintas (precios, base de datos, API, notificaciones) terminan en la misma clase y en los mismos métodos. Además, la lógica de negocio depende de FastAPI: un worker, un script o una prueba que use `OrderService` recibe `HTTPException` en lugar de errores del dominio.

**Cambios que lo hacen evidente.**
- Pasar las notificaciones a una cola con un worker (el adicional 2) obliga a editar `confirm` en medio de la transacción que descuenta el stock.
- Renombrar la columna `products.price_cents` en `app/products.py` rompe `app/orders.py` (líneas 50, 51 y 102), aunque el contrato HTTP de productos no cambie.

---

## Relación con la refactorización (parte 5)

| Smell | Refactorizaciones candidatas |
| --- | --- |
| 1. Duplicated Code | *Extract Function* para el cálculo de precios y para "obtener pedido pendiente" |
| 2. Long Method | *Extract Function* y *Split Phase* (calcular, luego persistir) |
| 3. Long Parameter List con Flag Argument | *Introduce Parameter Object* (pasar `OrderInput`) y *Remove Flag Argument* (separar `create` y `update`) |
| 4. Primitive Obsession | *Replace Magic Literal* y tablas de descuento y envío por categoría y tipo |
| 5. Divergent Change | *Extract Class* (calculadora de precios) y excepciones de dominio traducidas a HTTP en las rutas |
