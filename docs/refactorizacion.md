# 5. Refactorización

- **Revisión inicial (antes de refactorizar):** `1200e73`. Es el código de `969cbdb` más las pruebas de la parte 2.
- **Revisión final:** el commit que incluya este documento.
- **Archivo refactorizado:** `app/orders.py`, de 235 a 223 líneas. `app/customers.py`, `app/products.py`, `app/database.py` y `main.py` no cambian.

Se aplicaron cuatro técnicas del catálogo de Fowler (*Refactoring*, 2.ª ed.). Se mantienen las rutas, los cuerpos y códigos HTTP, los mensajes de error y su orden de evaluación, las reglas de negocio, el esquema SQLite y la transacción única por operación. Los smells mencionados están descritos en [code-smells.md](code-smells.md).

---

## Técnica 1: Extract Function

**Problema.** Smells 1 (Duplicated Code) y 2 (Long Method). El cálculo de descuento y envío estaba copiado en `save` y `quote`. La secuencia "buscar pedido, 404, comprobar pendiente, 409" se repetía en cuatro métodos. Y `save` tenía 58 líneas con ocho responsabilidades.

**Dónde.** Funciones extraídas en `app/orders.py`:

| Función | Líneas | Reemplaza |
| --- | --- | --- |
| `calculate_totals(category, shipping, subtotal)` | 38-47 | Los dos bloques de descuento y envío (antes 52-64 y 103-116) |
| `OrderService._price(connection, data)` | 130-141 | La búsqueda de cliente y productos, y el subtotal (antes 41-51 y 94-102) |
| `OrderService._find_order` y `_find_pending` | 156-166 | "Buscar pedido + 404 + 409", repetido en `save`, `confirm`, `cancel` y `delete` |
| `OrderService._detail(connection, order_id)` | 168-174 | La lectura del pedido con sus líneas (antes en `save` 85-89 y en `get` 120-127) |
| `_insert_lines` y `_order_values` | 143-153 | La inserción de líneas y la tupla de columnas |

**Antes** (`save` y `quote` repetían este bloque):

```python
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
```

```python
    def cancel(self, order_id):
        with self.database.connect() as connection:
            order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if order is None:
                raise HTTPException(404, "Pedido no encontrado")
            if order["status"] != "pending":
                raise HTTPException(409, "Solo puede cancelar pedidos pendientes")
            ...
```

**Después:**

```python
def calculate_totals(category, shipping, subtotal):
    discount = subtotal * DISCOUNT_PERCENT[category] // 100
    if shipping == "pickup":
        delivery = 0
    elif shipping == "standard":
        delivery = 0 if subtotal >= FREE_SHIPPING_FROM_CENTS else STANDARD_SHIPPING_CENTS
    else:
        delivery = EXPRESS_SHIPPING_CENTS
    return {"subtotal_cents": subtotal, "discount_cents": discount,
            "shipping_cents": delivery, "total_cents": subtotal - discount + delivery}

class OrderService:
    def quote(self, data):
        with self.database.connect() as connection:
            _, _, totals = self._price(connection, data)
            return totals

    def cancel(self, order_id):
        with self.database.connect() as connection:
            self._find_pending(connection, order_id, "Solo puede cancelar pedidos pendientes")
            ...
```

**Por qué mejora.**
- Cada regla de precio tiene un solo lugar. `quote`, `create` y `update` llaman a la misma función, así que ya no pueden dar totales distintos.
- `calculate_totals` no depende de la base de datos. Ahora se prueba con una llamada directa (`test_calculate_totals_without_database`), mientras que antes había que insertar clientes y productos en SQLite.
- Cada método público se lee como una secuencia de pasos con nombre.

---

## Técnica 2: Replace Magic Literal

**Problema.** Smell 4 (Primitive Obsession). Los porcentajes 10 y 15, el umbral 10000, los importes 1000 y 2500, y los estados `"pending"`, `'confirmed'` y `'cancelled'` aparecían como literales repetidos. La rama `else: discount = 0` le daba 0 % a cualquier categoría desconocida sin avisar.

**Dónde.** `app/orders.py`, líneas 6-13. Se usan en `calculate_totals`, `_find_pending`, `confirm` y `cancel`.

**Antes:**

```python
            if customer["category"] == "premium":
                discount = subtotal * 10 // 100
            elif customer["category"] == "business":
                discount = subtotal * 15 // 100
            else:
                discount = 0
...
            connection.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
            return {"id": order_id, "status": "cancelled"}
```

**Después:**

```python
PENDING = "pending"
CONFIRMED = "confirmed"
CANCELLED = "cancelled"

DISCOUNT_PERCENT = {"regular": 0, "premium": 10, "business": 15}
FREE_SHIPPING_FROM_CENTS = 10_000
STANDARD_SHIPPING_CENTS = 1_000
EXPRESS_SHIPPING_CENTS = 2_500
...
    discount = subtotal * DISCOUNT_PERCENT[category] // 100
...
            connection.execute("UPDATE orders SET status = ? WHERE id = ?", (CANCELLED, order_id))
            return {"id": order_id, "status": CANCELLED}
```

**Por qué mejora.**
- Las reglas de negocio del README se leen en un solo bloque, con nombres.
- La cadena `if/elif` de categorías pasa a ser una tabla. Una categoría sin descuento definido ya no recibe 0 % en silencio: falla con `KeyError`.
- `test_every_customer_category_has_a_discount` comprueba que las categorías aceptadas por `CustomerInput` y las de `DISCOUNT_PERCENT` sean las mismas. Así, agregar `vip` en un archivo y olvidarlo en el otro hace fallar la suite. Antes se cobraba el precio completo sin ningún error (ver smell 4).

---

## Técnica 3: Introduce Parameter Object

**Problema.** Smell 3 (Long Parameter List). `save` recibía siete parámetros posicionales. Las rutas ya tenían un `OrderInput` validado, pero lo desarmaban campo por campo. Intercambiar dos `str` (por ejemplo `city` y `postal_code`) no producía ningún error.

**Dónde.** `OrderService.create` (59-68), `OrderService.update` (70-82), `_order_values` (143-146) y las rutas `create_order` (186-187) y `update_order` (201-202).

**Antes:**

```python
    def save(self, customer_id, address, city, postal_code, shipping, items, order_id=None):
...
@router.post("", status_code=201)
def create_order(data: OrderInput, request: Request):
    return OrderService(request.app.state.database).save(
        data.customer_id, data.address, data.city, data.postal_code, data.shipping, data.items,
    )
```

**Después:**

```python
    def create(self, data):
...
    @staticmethod
    def _order_values(data, category, totals):
        return (data.customer_id, category, data.address, data.city, data.postal_code, data.shipping,
                totals["subtotal_cents"], totals["discount_cents"], totals["shipping_cents"], totals["total_cents"])
...
@router.post("", status_code=201)
def create_order(data: OrderInput, request: Request):
    return OrderService(request.app.state.database).create(data)
```

**Por qué mejora.**
- El servicio recibe el mismo objeto que valida Pydantic. Los campos se leen por nombre, así que no se pueden cruzar por posición.
- Agregar un campo al pedido ya no obliga a cambiar la firma ni las llamadas. Basta con el modelo, `_order_values` y el SQL. El *data clump* `address`/`city`/`postal_code` viaja dentro de `OrderInput`.

---

## Técnica 4: Remove Flag Argument

**Problema.** Smell 3 (Flag Argument) y parte del smell 2. `order_id=None` decidía si `save` creaba o editaba, con tres puntos de bifurcación (antes en las líneas 35, 67 y 74).

**Dónde.** `OrderService.create` (59-68) y `OrderService.update` (70-82).

**Antes:**

```python
    def save(self, customer_id, address, city, postal_code, shipping, items, order_id=None):
        with self.database.connect() as connection:
            if order_id is not None:
                old = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
                ...
            if order_id is None:
                cursor = connection.execute("""INSERT INTO orders(...) ...""", values)
                order_id = cursor.lastrowid
            else:
                connection.execute("""UPDATE orders SET ... WHERE id = ?""", (*values, order_id))
                connection.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
```

**Después:**

```python
    def create(self, data):
        with self.database.connect() as connection:
            category, lines, totals = self._price(connection, data)
            cursor = connection.execute("""INSERT INTO orders(...) VALUES (...)""",
                                        self._order_values(data, category, totals))
            self._insert_lines(connection, cursor.lastrowid, lines)
            return self._detail(connection, cursor.lastrowid)

    def update(self, order_id, data):
        with self.database.connect() as connection:
            self._find_pending(connection, order_id, "Solo puede editar pedidos pendientes")
            category, lines, totals = self._price(connection, data)
            connection.execute("""UPDATE orders SET ... WHERE id = ?""",
                               (*self._order_values(data, category, totals), order_id))
            connection.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            self._insert_lines(connection, order_id, lines)
            return self._detail(connection, order_id)
```

**Por qué mejora.**
- Cada operación tiene un nombre que dice lo que hace y un solo camino de ejecución.
- Crear y editar pueden evolucionar por separado, por ejemplo para la idempotencia de `POST /orders` del adicional 1, sin agregar más ramas al mismo método.
- `update` conserva el orden original de validación: pedido (404), estado (409), cliente (404) y productos (404). Todo sigue dentro de una sola transacción.

---

## Pruebas antes y después

```powershell
py -m uv run pytest --cov --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
```

| | Revisión inicial `1200e73` | Refactorizada |
| --- | --- | --- |
| Pruebas | 96 aprobadas | 101 aprobadas |
| Cobertura total | 99,67 % (302/303) | 99,66 % (289/290) |
| `app/orders.py` | 163 sentencias, 100 % | 150 sentencias, 100 % |

Las pruebas se corrieron primero **sin modificarlas** contra el código refactorizado. Todas las pruebas HTTP, de persistencia y de validación pasaron. Solo fallaron, con `AttributeError: 'OrderService' object has no attribute 'save'`, las pruebas unitarias que llamaban directamente al método eliminado: `test_saved_order_stores_the_same_totals_as_the_quote` y los 18 casos de `test_save_and_quote_apply_the_same_rules`.

En esas pruebas se cambió solo la llamada (`save(...)` pasó a `create(data)`) y el nombre de la segunda (`test_create_and_quote_apply_the_same_rules`). Las aserciones no cambiaron. Se agregaron 5 pruebas nuevas: 4 casos de `test_calculate_totals_without_database` y `test_every_customer_category_has_a_discount`.

Salida completa: [evidencias/pruebas-cobertura-final.txt](evidencias/pruebas-cobertura-final.txt).

---

## Limitaciones pendientes

- **Divergent Change (smell 5), resuelto a medias.** El cálculo de precios ya está separado, pero `OrderService` sigue lanzando `HTTPException`, lo que la acopla a FastAPI. El siguiente paso sería definir excepciones de dominio y traducirlas a HTTP en las rutas o con un *exception handler* en `main.py`. Se dejó fuera porque toca el contrato de errores de todos los módulos y no era necesario para los objetivos de esta entrega.
- **Acceso directo a tablas de otros módulos.** `OrderService` sigue leyendo `customers` y `products` y descontando stock con SQL propio, porque esa operación tiene que ocurrir en la misma transacción que la confirmación. Separarlo exigiría repositorios compartidos o un servicio de inventario que reciba la conexión.
- **Estados duplicados en el esquema.** `app/database.py` mantiene `DEFAULT 'pending'` en el SQL de creación de la tabla. Es el mismo valor que `PENDING`, pero no está enlazado a la constante.
- **Categorías declaradas en dos archivos.** Siguen definidas en `CustomerInput` (`Literal`) y en `DISCOUNT_PERCENT`. No se unificaron para no acoplar el módulo de clientes al de pedidos; la prueba `test_every_customer_category_has_a_discount` detecta si se desincronizan.
- **Notificaciones síncronas.** Siguen dentro de la transacción de `confirm`. Es el comportamiento pedido en la base; el adicional 2 lo cambiaría.
