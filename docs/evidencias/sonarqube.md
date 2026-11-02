# 3. Análisis con SonarQube local (inicial)

Fecha: 2026-11-02 · Código analizado: revisión `969cbdb` (sin refactorizar) más las pruebas de la parte 2.

## Entorno

| Herramienta | Versión |
| --- | --- |
| SonarQube | Community Build 26.10.0.133078 (imagen `sonarqube:community`, `compose.yaml`) |
| SonarScanner CLI | 8.1.0.6389 (imagen `sonarsource/sonar-scanner-cli`) |
| Perfil de calidad (Python) | **Sonar way core**, integrado y predeterminado, 232 reglas |
| Quality Gate | El predeterminado de la instancia (sin cambios) |

SonarScanner CLI se ejecutó en Docker, en la misma red que el contenedor de SonarQube. Así no hace falta instalar Java ni el scanner en Windows.

## Comandos

```powershell
docker compose up -d
py -m uv run pytest --cov --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
powershell -ExecutionPolicy Bypass -File scripts\sonar-scan.ps1
```

[scripts/sonar-scan.ps1](../../scripts/sonar-scan.ps1) pide el token de forma oculta, lo pasa al contenedor como `SONAR_TOKEN` y lo elimina al terminar. El proyecto se creó como local, con la clave `tienda-lab`. `sonar-project.properties` define las fuentes (`app`, `main.py`), las pruebas (`tests`) y el reporte `coverage.xml`.

## Resultado (Overall Code)

| Métrica | Valor |
| --- | --- |
| Quality Gate | Passed |
| Security / Reliability / Maintainability | 0 issues abiertos, calificación A en las tres |
| Accepted issues | 0 |
| Security Hotspots | 0 |
| Coverage | 99,7 % sobre 303 líneas por cubrir |
| Duplications | 0,0 % sobre 481 líneas |
| Líneas de código | 393 |

La cobertura coincide con la de pytest: 302 de 303 sentencias, 99,67 %. La única línea sin cubrir es `main.py:38`, `uvicorn.run(...)` dentro de `if __name__ == "__main__"`, que solo se ejecuta al iniciar el servidor manualmente.

### Corrección del reporte de cobertura

El primer análisis mostró **92,0 %** y esta advertencia:

> Cannot resolve the file path 'main.py' of the coverage report, the file does not exist in all 'source'.

Con `source = ["app", "main"]`, coverage.py escribía en `coverage.xml` las raíces `<source></source>` (vacía, la de `main.py`) y `<source>app</source>`. SonarQube descarta la raíz vacía, no encontraba `main.py` y contaba todas sus líneas como no cubiertas: 277 de 301 líneas, es decir 92 %.

Se cambió la configuración de coverage en `pyproject.toml`. El código de la aplicación no se tocó:

```toml
[tool.coverage.run]
source = ["."]
omit = ["tests/*"]
relative_files = true
```

Se miden los mismos archivos (`app/` y `main.py`, 303 sentencias) y no se excluye código de aplicación. Las rutas quedan relativas a la raíz (`main.py`, `app/orders.py`), bajo `<source>.</source>`.

La advertencia restante, *Missing blame information for 7 files*, corresponde a los 7 archivos de pruebas que aún no tenían commit. SonarQube usa `git blame` para atribuir líneas y no afecta las métricas.

## Interpretación de los hallazgos

SonarQube no reporta issues con el perfil **Sonar way core**. Eso no significa que el código no tenga problemas de mantenimiento. Las reglas del perfil detectan errores probables, vulnerabilidades y malas prácticas locales: variables sin usar, excepciones genéricas, complejidad cognitiva sobre el umbral, etc. Los problemas de diseño de este laboratorio no producen un patrón que esas reglas reconozcan:

- **La lógica de precios está duplicada** entre `OrderService.save` y `OrderService.quote` (`app/orders.py`). Duplications marca 0,0 % porque el detector de SonarQube busca secuencias de tokens idénticas: los dos bloques usan nombres distintos (`shipping` frente a `data.shipping`) y `save` intercala `lines.append(...)`, así que las secuencias no coinciden.
- **`save` concentra varias responsabilidades** (validar el estado, buscar el cliente y los productos, calcular, insertar o actualizar, armar la respuesta) y recibe 7 parámetros más un `order_id=None` que actúa como bandera para elegir entre crear y editar. Ambos valores quedan por debajo de los umbrales de las reglas de complejidad y de cantidad de parámetros.
- **El servicio lanza `HTTPException`**, lo que acopla la lógica de negocio a FastAPI, y las categorías y los tipos de envío son cadenas sueltas. Son decisiones de diseño que ninguna regla del perfil evalúa.

Por eso los code smells se documentan a partir de la revisión manual (parte 4). SonarQube aporta la evidencia complementaria: cobertura, ausencia de bugs o vulnerabilidades y la línea base para comparar después de refactorizar.

El Quality Gate aprobó, pero no es la medida principal de esta entrega: el gate evalúa sobre todo el código nuevo, y en el primer análisis no hay un periodo previo con el cual comparar.

## Capturas

| Captura | Contenido |
| --- | --- |
| [quality-gate-real.png](capturas/quality-gate-real.png) | Summary, Overall Code: Passed, 0 issues, 99,7 % de cobertura, 0,0 % de duplicación |
| [sonar-summary.png](capturas/sonar-summary.png) | Primer análisis, con el 92,0 % causado por el error de rutas descrito arriba |
| [issues-sonar.png](capturas/issues-sonar.png) | Pestaña Issues sin hallazgos; en el pie, la versión v26.10.0.133078 |
| [quality-profile.png](capturas/quality-profile.png) | Perfiles de Python: *Sonar way core* predeterminado, 232 reglas |

El análisis final, después de refactorizar, se agregará con las mismas capturas.
