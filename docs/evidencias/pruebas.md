# 2. Pruebas y cobertura (inicial)

Fecha: 2026-11-02 · Código de aplicación: revisión `969cbdb`, sin cambios.

## Comando

```powershell
py -m uv run pytest --cov --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
```

## Resultado

| | Pruebas | Cobertura de líneas |
| --- | --- | --- |
| Suite inicial (`tests/test_orders.py`) | 4 | 67 % |
| Suite ampliada | 87 | **99,67 %** (302/303) |

| Archivo | Antes | Después |
| --- | --- | --- |
| `app/customers.py` | 49 % | 100 % |
| `app/orders.py` | 63 % | 100 % |
| `app/products.py` | 71 % | 100 % |
| `app/database.py` | 100 % | 100 % |
| `main.py` | 92 % | 96 % (falta la línea 38, `uvicorn.run` bajo `__main__`) |

La salida completa está en [pruebas-cobertura-inicial.txt](pruebas-cobertura-inicial.txt).

## Organización

Cada prueba usa su propia base SQLite en `tmp_path` y crea sus propios datos (`tests/conftest.py`).

**Unitarias.** Llaman a `OrderService` y a los modelos directamente, sin HTTP.

- `test_pricing.py`: descuentos por categoría, truncado a centavos, costos de envío, el umbral de envío gratis (9999 frente a 10000) aplicado sobre el subtotal antes del descuento, la suma de varias líneas y que cotizar no reserva stock. Incluye una prueba de que `save` y `quote` dan los mismos totales en las 9 combinaciones de categoría y envío.
- `test_validation.py`: validación de `OrderInput`, `CustomerInput` y `ProductInput` (límites, tipos estrictos, campos extra, productos repetidos, valores por defecto).

**Integración de la API.**

- `test_products_api.py` y `test_customers_api.py`: CRUD, orden de los listados, `404`, `422`, correo duplicado (`409`) y que no se pueda eliminar un recurso que está en un pedido.
- `test_orders_api.py`: la cotización coincide con el pedido creado, listado resumido frente a detalle, `404` por cliente, producto o pedido inexistente, conservación de precios y categoría, `PUT` que recalcula con los valores actuales, un `PUT` fallido que no modifica nada, estados finales tras confirmar o cancelar, stock exacto y stock insuficiente, la notificación al correo del cliente y la eliminación en cascada de las líneas.
- `test_orders.py`: la suite original, sin cambios.

**Persistencia.**

- `test_persistence.py`: creación de la carpeta de la base, commit y rollback de `Database.connect`, claves foráneas activas, datos que sobreviven a un reinicio, `LAB_DB_PATH` y la respuesta `503` cuando SQLite no está disponible.

No se excluyó código ni se redujo la meta. La configuración de coverage se ajustó solo para que SonarQube resuelva la ruta de `main.py`; los archivos medidos son los mismos (ver [sonarqube.md](sonarqube.md)).

## Capturas

| Captura | Contenido |
| --- | --- |
| [cobertura-pytest.png](capturas/cobertura-pytest.png) | Comando completo: 87 pruebas aprobadas, tabla de cobertura y meta del 80 % alcanzada |
| [htmlcov-index.png](capturas/htmlcov-index.png) | Reporte HTML de coverage (`htmlcov/index.html`) |
| [pytest-evidencia.png](capturas/pytest-evidencia.png) | Ejecución de `pytest` sin cobertura: 87 aprobadas |
