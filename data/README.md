# Recursos de datos del proyecto

Archivos en `data/dictionaries/` — **recursos propios** del anonimizador IALAB.

| Archivo | Descripción | Datos reales |
|---------|-------------|--------------|
| `regex_limpio_v2.json` | Catálogo de expresiones regulares para detección judicial argentina | No contiene documentos ni expedientes |
| `nombres.json` | Lista de nombres propios frecuentes (validación heurística) | Nombres genéricos de uso público |
| `apellidos.json` | Lista de apellidos frecuentes en Argentina | Apellidos genéricos de uso público |
| `formulas_judiciales.json` | Palabras de contexto para filtros (no PII) | Lexico genérico |

**No incluyen:** corpus judiciales confidenciales, sentencias reales, ni datos personales.

**No distribuir:** documentos cargados, exportaciones con datos originales,
logs ni bases SQLite de una configuración de desarrollo que active persistencia.

En el paquete portable, solo se empaquetan los diccionarios (solo lectura).
La instancia de uso personal mantiene las sesiones en memoria y no crea
`sessions.db`. El almacenamiento SQLite de `SessionStore` es opcional y está
desactivado en la aplicación distribuida.

El motor de personas usa los catálogos cargados durante la ejecución; agregar
nombres no requiere regenerar expresiones regulares. En el portable, los
archivos de `data/dictionaries/` junto al ejecutable complementan los recursos
de `_internal/data/dictionaries/`. Reiniciá la aplicación después de editarlos.
Cada archivo debe contener una lista JSON no vacía de cadenas de texto.

`/health` informa disponibilidad, cantidad de entradas normalizadas y cantidad
de archivos leídos. Las diferencias entre el número de filas y el de entradas
se deben a duplicados, mayúsculas y tildes. Un catálogo de personas faltante,
vacío o inválido produce un error visible y no reemplaza el análisis anterior.

Las familias de identificadores tienen una implementación común en
`app/detection/identifiers.py`. Sus reglas históricas del catálogo regex se
conservan como recurso, pero no se ejecutan en paralelo con el detector actual.
