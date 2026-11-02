# 1. Ejecución de la aplicación

Fecha: 2026-11-02 · Revisión: `969cbdb`

## Entorno

| Herramienta | Versión |
| --- | --- |
| Sistema operativo | Windows 11 Home 10.0.26300 |
| Python (entorno `.venv` creado por uv) | 3.14.3 |
| uv | 0.13.6 (329bf9448 2026-10-26 x86_64-pc-windows-msvc) |
| FastAPI | 0.162.0 |
| Uvicorn | 0.54.0 |
| Pydantic | 2.14.1 |

uv se instaló con `python -m pip install --user uv`. Por eso se invoca como `python -m uv`. Si `uv` está en el PATH, `uv` equivale a `python -m uv`.

## Comandos

Desde la raíz del repositorio, con una base vacía (sin `data/store.sqlite3`):

```powershell
python -m uv --version
python -m uv run python --version
python -m uv sync --locked
python -m uv run main.py
```

Las peticiones se hicieron con `curl` contra `http://127.0.0.1:8000`, en el orden del recorrido inicial del README.

## Resultados

| Paso | Petición | Esperado | Obtenido |
| --- | --- | --- | --- |
| 1 | `POST /customers` | Cliente creado | `201`, `id` 1, categoría `premium` |
| 2 | `POST /products` | Producto creado | `201`, `id` 1, `stock` 5 |
| 3 | `POST /orders/quote` | 5000 / 500 / 1000 / 5500 | `200`, subtotal 5000, descuento 500, envío 1000, total 5500 |
| 3 | `POST /orders` | Pedido pendiente con los mismos totales | `201`, `status` `pending`, total 5500 |
| 4 | `POST /orders/1/confirm` | Pedido confirmado | `200`, `status` `confirmed` |
| 5 | `GET /products/1` | `stock` 3 | `200`, `stock` 3 |
| 6 | `GET /orders/1/notifications` | Una notificación | `200`, 1 notificación para `ana@example.com` |
| 7 | `POST /orders/1/confirm` (repetido) | `409` sin otro descuento | `409` `"El pedido ya no está pendiente"`; `GET /products/1` mantiene `stock` 3 |

Los 7 pasos del recorrido dan el resultado esperado.

## Archivos de evidencia

- [recorrido.txt](recorrido.txt): cada petición con su cuerpo, la respuesta y el código HTTP.
- [servidor-log.txt](servidor-log.txt): log de Uvicorn durante el recorrido (arranque y una línea por petición).

## Capturas (Swagger)

| Paso | Captura |
| --- | --- |
| Swagger | [Screenshot_1.png](capturas/Screenshot_1.png) |
| 1. Crear cliente | [crear-usuario.png](capturas/crear-usuario.png) |
| 2. Crear producto | [crear-producto.png](capturas/crear-producto.png) |
| 3. Cotizar (5000 / 500 / 1000 / 5500) | [quote.png](capturas/quote.png) |
| 3. Crear pedido | [create-order.png](capturas/create-order.png) |
| 4. Confirmar | [confirm-order.png](capturas/confirm-order.png) |
| 5. Stock en 3 | [get-stock.png](capturas/get-stock.png) |
| 6. Notificación | [notifications.png](capturas/notifications.png) |
| 7. Reconfirmar: `409` | [confirm-order-again.png](capturas/confirm-order-again.png) |
