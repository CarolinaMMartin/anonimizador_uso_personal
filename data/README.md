# Recursos de datos del proyecto

Archivos en `data/dictionaries/` — **recursos propios** del anonimizador IALAB.

| Archivo | Descripción | Datos reales |
|---------|-------------|--------------|
| `regex_limpio_v2.json` | Catálogo de expresiones regulares para detección judicial argentina | No contiene documentos ni expedientes |
| `nombres.json` | Lista de nombres propios frecuentes (validación heurística) | Nombres genéricos de uso público |
| `apellidos.json` | Lista de apellidos frecuentes en Argentina | Apellidos genéricos de uso público |
| `formulas_judiciales.json` | Palabras de contexto para filtros (no PII) | Lexico genérico |

**No incluyen:** corpus judiciales confidenciales, sentencias reales, ni datos personales.

**No distribuir:** `data/sessions.db` (base SQLite local de sesiones de desarrollo/uso).

En el paquete portable, solo se empaquetan los diccionarios (solo lectura).
La base `sessions.db` se crea en runtime junto al ejecutable si el usuario procesa documentos.
