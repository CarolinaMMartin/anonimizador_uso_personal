# Contribuir al Anonimizador Judicial

El proyecto procesa documentos localmente con regex, Presidio y spaCy. Mantener el control del usuario sobre las detecciones, agrupaciones y exportaciones, y utilizar únicamente ejemplos ficticios en código, tests, Issues y documentación.

## Entorno

Python 3.11–3.13. La entrega Windows 3.3.12 se verifica con Python 3.13.15. Node.js se utiliza para las pruebas del frontend, sin dependencias npm.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\run_dev.py
```

En macOS/Linux usar `.venv/bin/python`. El instalador utiliza el modelo fijo 3.8.0; el inicio busca un puerto disponible e informa la dirección. En `/health`, las capas se consultan en `nlp_layers.presidio.available` y `nlp_layers.spacy.available`.

## Verificación

```powershell
.venv\Scripts\python -m pip check
.venv\Scripts\python -m pytest tests -q
node --test tests/frontend_session.test.cjs
.venv\Scripts\python scripts\audit_repository.py
```

Los tests del portable se omiten si aún no se construyó; deben pasar sin omisiones para una entrega. Ver [DEPLOY.md](docs/DEPLOY.md).

Agregar regresiones que representen el comportamiento general del problema. Cubrir nombres nuevos, mayúsculas, tildes, orden de apellido/nombre, iniciales, partículas y ambigüedad. No introducir listas de excepciones ligadas a un documento real.

La normalización de nombres y la identidad se resuelven en el backend. El frontend utiliza esos grupos. La coincidencia de un apellido compartido no basta para fusionar personas. El análisis NLP recorre fragmentos superpuestos del texto completo; preservar posiciones absolutas y cancelación entre fragmentos.

Después de modificar los catálogos, ejecutar `python scripts/update_name_rules.py` y las pruebas de nombres. No introducir llamadas de red durante el análisis, telemetría o carga automática de modelos generativos.

## Proponer cambios

Para cambios grandes, abrir un Issue con el problema y alcance; para correcciones pequeñas, presentar directamente un PR desde una rama basada en `main`. Describir el comportamiento final, la validación y cualquier limitación. No afirmar que se probó una plataforma o interfaz que no se verificó.

Mantener versiones fijadas, avisos de terceros y manuales consistentes con el comportamiento. Las contribuciones se distribuyen bajo Apache 2.0 conforme a [LICENSE](LICENSE); el uso del logo y marca se rige por [NOTICE](NOTICE).

La función de personas conocidas es una [propuesta pendiente](docs/propuestas/PERSONAS_CONOCIDAS.md) y no se incluye en 3.3.12.
