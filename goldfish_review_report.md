# Goldfish Annotated Review Report

Status: resolved — una ronda autorizada; fase de revisión cerrada y entrega a implementación. No equivale a convergencia de dos rondas.

**Target:** `docs/revision-egm/correcciones_pendientes.md`, full file, líneas 1–45 antes de incorporar precisiones.

Los dos agentes reales se lanzaron por separado con `fork_turns: none`. Ambos informaron lectura íntegra del target, su persona, el estándar y los ocho archivos de contexto requeridos. No se proporcionó historial de conversación. El aislamiento de historial no implica aislamiento del sistema de archivos ni de instrucciones del host.

| Revisor solicitado | Perfil instalado | Estándar instalado | Estado |
| --- | --- | --- | --- |
| codebase_details | `agents/codebase_details.md` (`egm-codebase-details`) | `resources/document_standards/implementation-readiness-standard.md` | completed |
| implementation_readiness | `agents/implementation_readiness.md` (`egm-implementation-readiness`) | `resources/document_standards/implementation-readiness-standard.md` | completed |

Raíz del plugin: `C:/Users/CarolinaM/.codex/plugins/cache/egm/egm/0.1.0/`. Contexto leído por ambos: `README.md`, `docs/MANUAL_USUARIO.md`, `app/services/detections.py`, `app/services/clusters.py`, `app/anonymize/apply.py`, `app/models/schemas.py`, `app/api/routes_export.py`, `frontend/app.js`. Ambos consultaron además rutas y servicios locales relacionados; ninguno ejecutó pruebas ni escribió archivos durante la revisión. No hubo revisores fallidos ni reintentos.

## Prioritized Findings & AI Suggestions

### codebase_details-1-1 — codebase_details — Severity: Major

- **Affected Scope:** plan original, líneas 12–17 y 38.
- **Discrepancy Description:** falta definir cómo conservar el orden de las decisiones al vaciar cambios pendientes. `scheduleDetectionPatch` actualiza un Map sin cambiar el orden de inserción; `flushPendingSaves` recorre sus claves. A→B→A puede enviarse A→B, dando prioridad a B.
- **Rationale:** prioridad provisional y aceptación posterior del contador del servidor no corrigen una inversión del orden de las acciones humanas.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** precisar reinserción de la fila al actualizar su entrada pendiente, tokens de acción independientes de valores, reconciliación de respuestas y regresión A→B→A antes del debounce. Incorporado en «Precisiones incorporadas tras la ronda 1».

### codebase_details-1-2 — codebase_details — Severity: Major

- **Affected Scope:** líneas 21–24 y 39.
- **Discrepancy Description:** conservar el mapa Unicode actual deja sin resolver acentos descompuestos. `buildNormMap` omite marcas sin extender el extremo anterior; `jose` sobre `Jose\u0301` produce `[0,4)` en vez de `[0,5)`.
- **Rationale:** con límites completos se rechaza la coincidencia o, en parcial, queda un acento suelto.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** sustituir la conservación literal del mapa por iteración de puntos Unicode y extensión de extremos hasta abarcar marcas descartadas. Alinear contador, resaltado, petición y validación backend. Agregar expectativa exacta `[0,5)`. Incorporado en las precisiones Unicode. Vinculado a implementation_readiness-1-1.

### codebase_details-1-3 — codebase_details — Severity: Major

- **Affected Scope:** líneas 22–24 y 39.
- **Discrepancy Description:** el avance tras una coincidencia rechazada debe aplicarse también al backend. Filtrar `re.finditer` puede saltar una repetición completa: `Ana Ana; xAna Ana Ana` produce candidata rechazada `[10,17)` y omite la válida `[14,21)`.
- **Rationale:** conservar la selección original no recupera esa otra repetición.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** establecer búsqueda iterativa en `_find_positions`: rechazo avanza un punto desde inicio, aceptación avanza al final. Añadir ese caso mínimo. Incorporado en las precisiones de búsqueda backend.

### implementation_readiness-1-1 — implementation_readiness — Severity: Major

- **Affected Scope:** líneas 21–24 y 39.
- **Discrepancy Description:** falta resolver los extremos de las coincidencias con acentos descompuestos; la nueva regla de marcas como parte de palabra contradice conservar el mapa actual.
- **Rationale:** el caso genérico de acentos descompuestos no define cómo obtener el intervalo completo.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** misma reparación de codebase_details-1-2; ambos IDs se conservan para trazabilidad. `Jose` y `José` deben localizar todo `Jose\u0301` en `[0,5)`.

### implementation_readiness-1-2 — implementation_readiness — Severity: Major

- **Affected Scope:** líneas 12–17 y 38.
- **Discrepancy Description:** el contrato de prioridad provisional no identifica la acción confirmada; una respuesta antigua puede coincidir en valor con otra edición y retirar su prioridad. La proyección local de una etiqueta tampoco alcanza los miembros del grupo que sí actualiza el servidor.
- **Rationale:** sin unidad de decisión y reglas para anidación/proyección pueden mostrarse ganadores distintos antes y después del guardado.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** una marca por acción pública, acumulación de afectados en llamadas anidadas, tokens locales por edición y proyección de etiquetas sobre miembros confirmados conocidos. Respuestas antiguas no eliminan un token posterior aunque repita valor. Agregar prueba con respuesta demorada y edición posterior. Incorporado; complementa codebase_details-1-1.

### implementation_readiness-1-3 — implementation_readiness — Severity: Major

- **Affected Scope:** línea 37.
- **Discrepancy Description:** la excepción que permite ajustar cualquier otro test deja abierta la lista de archivos modificables.
- **Rationale:** el estándar requiere rutas exactas para delimitar las modificaciones.
- **AI Suggestion:** PROPOSE FIX.
- **Justification / Proposed Edit:** eliminar esa autorización genérica, conservar la lista explícita y agregar solo `tests/test_review_empty_exports.py` para C5. Incorporado en fase D.

## Resolución de la ronda

Seis PROPOSE FIX aceptados e incorporados, con dos coincidencias temáticas vinculadas; cero CONTEST, ESCALATE o DECLINE. No se rebajaron severidades. La ronda no fue limpia antes de las reparaciones: produjo seis Major. Por instrucción explícita del usuario se cerró EGM y se continuó implementando, sin una segunda ronda ni solicitud de aprobación rutinaria. La ejecución posterior y sus resultados están registrados al final de `docs/revision-egm/correcciones_pendientes.md`; son evidencia de implementación, no una nueva ronda Goldfish.
