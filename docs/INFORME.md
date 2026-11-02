# Informe: Tienda Lab (pruebas, análisis estático y refactorización)

## Revisiones

| Revisión | Contenido |
| --- | --- |
| `969cbdb` | Código original del laboratorio |
| `1200e73` | **Revisión inicial (pre-refactor):** código original más las pruebas de la parte 2 (87) |
| `57a54df` | **Revisión final:** refactorización de `app/orders.py`, la ampliación de pruebas de la parte 4 y las pruebas adaptadas (101) |

## Contenido

| Parte | Documento |
| --- | --- |
| 1. Ejecutar la aplicación | [evidencias/ejecucion.md](evidencias/ejecucion.md) |
| 2. Pruebas y cobertura | [evidencias/pruebas.md](evidencias/pruebas.md) |
| 3. SonarQube, análisis inicial y final | [evidencias/sonarqube.md](evidencias/sonarqube.md) |
| 4. Code smells (5) | [code-smells.md](code-smells.md) |
| 5. Refactorización (4 técnicas) | [refactorizacion.md](refactorizacion.md) |
| 6. Diagramas de clases | [diagramas/README.md](diagramas/README.md) |

## Entorno

| Herramienta | Versión |
| --- | --- |
| Sistema operativo | Windows 11 Home 10.0.26300 |
| Python | 3.14.3 |
| uv | 0.13.6 |
| FastAPI / Uvicorn / Pydantic | 0.162.0 / 0.54.0 / 2.14.1 |
| pytest / pytest-cov | 9.1.1 / 7.1.0 |
| SonarQube | Community Build 26.10.0.133078 |
| SonarScanner CLI | 8.1.0.6389 (Docker) |
| Perfil de calidad | Sonar way core (Python, 232 reglas) |

## Comandos para reproducir

Desde la raíz del repositorio. Si `uv` está en el PATH, `py -m uv` equivale a `uv`.

```powershell
# Dependencias y aplicación (Swagger en http://127.0.0.1:8000/docs)
py -m uv sync --locked
py -m uv run main.py

# Pruebas y cobertura (genera coverage.xml y htmlcov/)
py -m uv run pytest --cov --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80

# SonarQube local (http://localhost:9000) y análisis
docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts\sonar-scan.ps1
docker compose down
```

Para comparar el estado inicial con el final, se hace `git checkout 1200e73` o `git checkout 57a54df` y se repiten los comandos de pruebas y análisis.

## Resumen de resultados

| | Inicial (`1200e73`) | Final (`57a54df`) |
| --- | --- | --- |
| Pruebas | 87 aprobadas (96 con la ampliación de la parte 4, sobre el mismo código) | 101 aprobadas |
| Cobertura de líneas | 99,67 % | 99,66 % |
| SonarQube | Passed, 0 issues, 0,0 % de duplicación, 99,7 % sobre 303 líneas, 393 líneas de código | Passed, 0 issues, 0,0 % de duplicación, 99,7 % sobre 290 líneas, 370 líneas de código |
| `OrderService` | `save` de 58 líneas con 7 parámetros y bandera; precios duplicados | `create` y `update` separados; `calculate_totals` único y probado sin base de datos |

## Cambios de configuración

- **`pyproject.toml`, `[tool.coverage.run]`:** `source = ["."]` y `omit = ["tests/*"]` en lugar de `source = ["app", "main"]`. Con la configuración original, SonarQube no resolvía la ruta de `main.py` y marcaba 92 % de cobertura. Se miden los mismos archivos. Detalle en [evidencias/sonarqube.md](evidencias/sonarqube.md).
- **`scripts/sonar-scan.ps1`:** ejecuta SonarScanner CLI en Docker y pide el token de forma oculta. No se guarda ningún token en el repositorio.

## Limitaciones pendientes

- **`OrderService` sigue acoplado a FastAPI**, porque lanza `HTTPException`, y sigue accediendo con SQL propio a las tablas `customers` y `products` (smell 5, resuelto parcialmente).
- **Las categorías de cliente se declaran en dos lugares** (`CustomerInput` y `DISCOUNT_PERCENT`). Una prueba detecta si se desincronizan.
- **El estado `pending` sigue como literal** en el esquema SQL (`app/database.py`).
- **SonarQube no detecta los smells de diseño documentados**, así que su resultado no mide la mejora de la refactorización. Solo confirma que no se introdujeron problemas nuevos. Además, Community Build no analiza vulnerabilidades de inyección.
- **La línea `main.py:38`** (`uvicorn.run` bajo `__main__`) no se cubre con pruebas.
- **Los adicionales 1, 2 y 3 no se implementaron.**

Detalle en [refactorizacion.md](refactorizacion.md#limitaciones-pendientes).

## No incluido en el repositorio

`.venv/`, `data/` (base SQLite), `coverage.xml`, `htmlcov/`, `.scannerwork/`, cachés y tokens. Todo está excluido en `.gitignore`.
