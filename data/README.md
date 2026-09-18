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
