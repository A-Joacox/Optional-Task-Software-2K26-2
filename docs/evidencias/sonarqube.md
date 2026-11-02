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

---

## Análisis final (después de refactorizar, revisión `57a54df`)

Mismo servidor, mismo perfil (*Sonar way core*), mismo Quality Gate y mismo script de análisis.

| Métrica (Overall Code) | Inicial (`1200e73`) | Final (`57a54df`) |
| --- | --- | --- |
| Quality Gate | Passed | Passed |
| Issues abiertos (Security / Reliability / Maintainability) | 0 / 0 / 0 | 0 / 0 / 0 |
| Security Hotspots | 0 | 0 |
| Duplications | 0,0 % sobre 481 líneas | 0,0 % sobre 469 líneas |
| Cobertura en pytest | 99,67 % (302/303) | 99,66 % (289/290) |
| Cobertura en SonarQube | 99,7 % sobre 303 líneas | 99,7 % sobre 290 líneas |
| Líneas de código (ncloc) | 393 | 370 |
| Advertencias del análisis | Cobertura de `main.py` (corregida) y *blame* en 7 archivos | Ninguna |
| Pruebas que generaron `coverage.xml` | 87 | 101 |

**Código nuevo del análisis final** (New Code, desde el 2 de noviembre de 2026; corresponde a las líneas cambiadas por la refactorización):

| Métrica | Valor | Condición del Quality Gate |
| --- | --- | --- |
| New issues | 0 | = 0 |
| Coverage | 100 % sobre 72 líneas nuevas | ≥ 80,0 % |
| Duplications | 0,0 % sobre 696 líneas nuevas | ≤ 3,0 % |

Estas condiciones son las del Quality Gate predeterminado. Se evalúan **solo sobre el código nuevo**, por eso el gate no refleja la calidad del código heredado, que no cambió.

**Interpretación.** SonarQube no cambia de veredicto, porque no reportaba nada antes de refactorizar. La mejora no se ve en sus métricas: el perfil no evalúa la duplicación de lógica ni los problemas de diseño que se corrigieron (ver [code-smells.md](../code-smells.md)). Lo que sí confirma el análisis final es que la refactorización no introdujo bugs, vulnerabilidades ni issues de mantenibilidad, y que la cobertura se mantuvo. La reducción de `app/orders.py` (de 163 a 150 sentencias) se refleja en las líneas por cubrir (de 303 a 290) y en las líneas de código (de 393 a 370).

El summary también muestra el aviso *Limited security analysis*: SonarQube Community Build no analiza vulnerabilidades de inyección (SQL injection, XSS). El 0 en Security vale dentro de ese alcance. En este código, las consultas SQL usan parámetros `?` en lugar de concatenar valores.

| Captura | Contenido |
| --- | --- |
| [sonar-summary-final.png](capturas/sonar-summary-final.png) | Summary del análisis final, Overall Code |
| [sonar-newcode-final.png](capturas/sonar-newcode-final.png) | Summary del análisis final, New Code: 370 líneas de código y condiciones del Quality Gate |
| [sonar-issues-final.png](capturas/sonar-issues-final.png) | Pestaña Issues sin hallazgos |
| [pytest-evidencia-final.png](capturas/pytest-evidencia-final.png) | 101 pruebas aprobadas y cobertura del 99,66 % |
