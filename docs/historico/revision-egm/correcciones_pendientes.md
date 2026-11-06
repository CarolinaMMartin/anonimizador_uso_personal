# Plan breve: C2, C3, C4 y C5

> Registro histórico del plan y su cierre para 3.4.3. Las restricciones,
> rutas y estados siguientes corresponden a esa revisión. La entrega vigente
> se documenta en el [README actual](../../../README.md).

Rama: `revision-egm`. Base: código local con C1, D1 y C6 ya corregidos y `2026-11-06_DRIFT_REPORT.md`. No habrá commits, push, publicaciones ni cambios de dependencias. Datos y descargas de prueba serán sintéticos. Se autoriza una única ronda EGM con `codebase_details` e `implementation_readiness`, ambos contra `implementation-readiness-standard`, sobre este archivo completo; incorporar observaciones justificadas y continuar implementando sin otra ronda ni aprobaciones rutinarias.

## 1. Estado actual y límites

`add_manual_detection` ya conserva el intervalo explícito además de las repeticiones; `getSelectionInPreview` ya conserva el Range DOM; `syncDetectionLabels` actualiza etiquetas sin desmontar inputs. Se preservan esas correcciones. Actualmente `anonymize_text` y la vista local fusionan solapamientos usando la primera etiqueta; la búsqueda admite subcadenas; cambiar categoría pierde etiquetas personalizadas; las rutas de editor/Word/PDF rechazan listas vacías. Los informes `VERIFICACION_*` no acreditan pruebas actuales.

## 2. Fase A: decisiones manuales y etiquetas (C2 y C4)

- Modificar `app/models/schemas.py`: añadir `Detection.manual_order: int = 0`, `SessionState.review_sequence: int = 0` y `Cluster.manual_placeholder: bool = False`. Los campos nuevos tienen valores por defecto para estados/clientes anteriores; las sesiones activas viven en memoria. No migrar bases ni archivos personales.
- Crear `app/services/review_state.py`: helper para asignar un contador creciente a detecciones afectadas por una decisión manual. El contador se obtiene del máximo del contador de sesión y las marcas existentes más uno. No se deriva de la hora. Las decisiones automáticas conservan orden cero.
- Modificar `app/services/detections.py`: asignar orden al agregar/reseleccionar, búsqueda manual, cambio de etiqueta/categoría y activación explícita. Cambiar una fila afecta todas sus posiciones, como hoy; no se extiende a otras identidades. Desactivar excluye esa fila, sin levantar la protección de otra fila activa que cubra el mismo texto. Eliminar permite que las restantes decidan el resultado. No consumir decisiones en peticiones inválidas.
- Modificar `app/services/clusters.py` y `app/api/routes_entities.py`: registrar las decisiones explícitas de confirmar, asignar, unir, separar, rechazar, reclasificar y editar reemplazo para las filas cuyo reemplazo se decide. Una acción sobre un grupo alcanza sus miembros, pero resolver un solapamiento no modifica grupos ni identidades. El refresco automático de sugerencias no recibe prioridad manual.
- C4: una categoría nueva conserva `placeholder` y su origen manual. Guardar el valor/origen antes de desvincular una fila del grupo, porque `_release_detections` puede regenerarlo. Propagar el origen manual desde el grupo a sus variantes en `_sync_cluster_to_detections`; editar una etiqueta desde una fila confirmada marca también la del grupo como manual. Reclasificar un grupo confirmado conserva su etiqueta si es manual, y regenera la automática; en grupos sugeridos conservar cada etiqueta manual. La asignación explícita a otro grupo sigue usando la etiqueta del destino: es una decisión de unión, no solo de categoría.
- Modificar `app/anonymize/apply.py`: compartir un resolutor de intervalos entre `anonymize_text` y `build_highlights`. Para cada componente de intervalos activos estrictamente solapados (no adyacentes), conservar toda su unión y elegir la etiqueta/categoría del mayor `manual_order`; a igualdad mantener la precedencia existente por inicio, mayor longitud y orden de lista. Un conflicto cambia solo el componente espacial: otras apariciones de las mismas filas mantienen sus etiquetas. No cambiar posiciones originales ni fusionar identidades. Mantener validación de rangos y `confirmed_only`.
- Modificar `frontend/app.js`: reproducir esa misma regla en la vista local y resaltados, incluyendo ediciones pendientes. Asignar prioridad local provisional a una acción explícita; las respuestas del servidor restablecen el orden confirmado sin pisar `localEdits`. Mostrar junto al campo editable las sustituciones efectivamente aplicadas cuando difieran por conflicto; una fila puede tener varias sustituciones según aparición. Actualizar esa información al editar, activar o desactivar y al recibir respuestas, conservando foco/cursor y C6.

## 3. Fase B: coincidencias completas por defecto (C3)

- Crear `app/services/matching.py` para la regla de límite: letras Unicode, números, marcas combinantes y guion bajo forman palabra. Los conectores `. @ / : + - '` entre caracteres de palabra continúan un dato; un `+` inicial seguido de dígito pertenece al número. Así `Ana` no coincide en `Mariana` ni en `Ana@example.test`, `123` no coincide en `123-456`, pero `Ana,` y `Ana.` al fin de frase sí admiten `Ana`. No es un parser de todos los formatos documentales.
- Modificar `_find_positions` para filtrar repeticiones por esos límites, salvo `allow_partial=True`. La selección original siempre se incluye exactamente, aunque sea parte de una palabra/dato: mantener C1 y D1. Conservar la comparación literal sin distinguir mayúsculas en selección; la lupa sigue ignorando tildes usando su mapeo Unicode actual.
- Modificar `app/models/schemas.py` (`SearchAndAnonymizeRequest`), `app/api/routes_actions.py` y `app/api/routes_detections.py`: `allow_partial: bool = False` en las dos entradas manuales y en la búsqueda. Validar en backend los límites y la correspondencia normalizada entre consulta y posiciones de búsqueda; devolver 400 ante rangos inválidos sin modificar la sesión. No limitar el intervalo explícito de selección por esta regla.
- Modificar `frontend/index.html`, `frontend/styles.css` y `frontend/app.js`: casilla desactivada por defecto «Permitir coincidencias parciales» en lupa y barra de selección. En selección explica que afecta repeticiones, no el fragmento elegido. En lupa el contador, marcas y envío usan la misma opción. Restablecer a completo al cargar otro documento y al iniciar una nueva selección; no guardar esta excepción en almacenamiento persistente. Avanzar una unidad Unicode tras coincidencias descartadas para no perder posteriores coincidencias válidas.

## 4. Fase C: sesión revisada sin detecciones (C5)

- Modificar `SessionState` en `app/models/schemas.py`: `has_review: bool = False`. Carga nueva permanece falsa; análisis exitoso, incluso con cero resultados, la vuelve verdadera. Operaciones manuales exitosas también, y eliminar la última fila no la borra. Fallos/cancelación no alteran el estado previo. Para compatibilidad con estados existentes, detecciones presentes también acreditan una revisión; una sesión recién cargada sin detecciones no.
- Modificar `app/api/routes_analyze.py` tras `run_full_analysis` exitoso, y el helper de revisión/manuales, para mantener esa marca. El análisis se realiza sobre copia como hoy, sin perder una revisión anterior si falla. Exponer el estado en `get_session`.
- Modificar `app/api/routes_export.py`: factorizar validación de documento cargado y revisado; usarla en preview, Word y PDF. No condicionar esas rutas a detecciones no vacías. Sesión inexistente: 404; cargada pero no revisada: 400 con indicación clara. CSV queda fuera del cambio y puede seguir rechazando tabla vacía.
- Conservar `resolve_export_text` en `app/export/export_utils.py`: `req.text is not None` tiene prioridad sobre regeneración, incluso si es cadena vacía. Ajustar `text_to_paragraphs` para no insertar «(documento vacío)» cuando el usuario vacía el editor: exportar un documento vacío. No reanalizar el texto editado.
- La UI conserva el control `editorSnapshot`/`reviewRevision`: después de eliminar la última fila se puede regenerar el editor, y las correcciones del editor se exportan como antes. Actualizar mensajes para distinguir «sin detecciones» de «sin analizar».

## 5. Fase D: documentación y validación

- Modificar `README.md` y `docs/MANUAL_USUARIO.md`: explicar prioridad de la última decisión, cobertura total del conflicto, sustituciones aplicadas por aparición, coincidencias completas/opción parcial, conservación de etiquetas manuales, y salida sin detecciones tras revisión. No afirmar conservación de maquetación original ni ampliar soporte de plataforma.
- Crear `tests/test_review_decisions.py`, `tests/test_complete_matching.py` y `tests/test_review_empty_exports.py`; modificar `tests/test_manual_review_regressions.py`, `tests/test_entity_reclassification.py`, `tests/test_search_and_anonymize.py`, `tests/test_person_identity.py` (solo alinear tres fixtures de consulta con sus intervalos bajo C3), `tests/test_highlight_coverage.py`, `tests/test_anonymization_safety.py`, `tests/frontend_session.test.cjs` y `tests/test_browser_manual_review.py` solo para regresiones y expectativas de las reglas que cambian. Lista cerrada; la única incorporación posterior es `scripts/test_portable_smoke.py`, con el ajuste concreto de intervalo documentado en las precisiones.
- C2: rangos iguales, contenidos, cruzados y cadena transitiva; anterior automática vs nueva manual y nueva manual vs anterior manual; la aparición no solapada de una fila conserva su identidad; desactivar/eliminar ganador; orden idéntico entre resolver, resaltado, tabla, editor y descargas. Incluir cambio de etiqueta/categoría y acciones de grupos.
- C3: `Ana y Mariana`, mayúsculas, acentos descompuestos, signos de puntuación, identificadores compuestos, parcial explícito, consulta dentro de un dato completo, selección original dentro de palabra, repetición solapada `121212` y offsets tras emoji. Bajo el nuevo valor por defecto, C1 exige cubrir `[2,6)`; con parcial explícito debe seguir conservándose la unión `[0,6)`.
- C4: etiqueta manual y automática en fila independiente, miembro confirmado y grupo completo; desactivadas no se reactivan al reclasificar; edición explícita simultánea prevalece. C5: recién cargado bloqueado, analizado vacío permitido, última fila eliminada/desactivada, error/cancelación conserva estado, texto editado y vacío respetados en Word/PDF.
- Escribir y ejecutar regresiones antes de sus correcciones, registrar fallos esperados y luego ejecutar las suites relacionadas. Pruebas reales con Playwright/Edge instalado, servidor local en puerto efímero, carga DOCX sintética, selección por arrastre, captura de cuerpos de petición, edición y descargas; no simular DOM ni exportadores. Comparar texto de vista/editor con DOCX mediante python-docx y PDF mediante pdfplumber. Comprobar C1, D1 y C6 de nuevo. Usar `build/egm-*` únicamente para artefactos generados de prueba.

## 6. Cierre

Crear `goldfish_review_report.md` para resultados originales de ambos revisores, IDs estables, decisiones PROPOSE FIX/CONTEST/DECLINE y resolución. Una ronda no se presentará como convergencia de dos rondas. Conservar el informe de deriva original como antecedente; registrar validación final en este plan y resumir resultados, revisores completados y pendientes reales en la respuesta final.


## Precisiones incorporadas tras la ronda 1

- Orden manual: una acción pública exitosa comparte una sola marca entre todas sus filas afectadas. `review_state.py` proporciona un contexto de acción y un decorador para servicios públicos; llamadas internas anidadas de la misma sesión acumulan afectados y solo la salida externa exitosa asigna el contador. Validaciones fallidas no lo consumen. La edición de un grupo se delimita también en `routes_entities.update_cluster`. La prioridad no altera membresía, posiciones ni filas ajenas a la acción.
- Frontend: cada edición diferida recibe un token local creciente independiente del valor. `pendingPatches` se elimina/reinserta al actualizar una fila, por lo que vaciar A→B→A envía B→A. El guardado captura el token; una respuesta solo retira los cambios locales si confirma ese mismo token, aunque el valor de una edición posterior coincida. Los cambios pendientes se proyectan en orden de token sobre la respuesta del servidor. Sus prioridades provisionales se sitúan por encima del orden confirmado, incluso si el contador avanzó por decisiones sobre filas ya eliminadas. Una etiqueta editada desde una variante confirmada se proyecta sobre todos los miembros conocidos del grupo; una activación solo sobre su fila. No se envía al backend la prioridad provisional. Probar A→B→A, respuesta demorada y repetición del mismo valor; exportación sigue esperando los guardados.
- Unicode: corregir `buildNormMap`, sin conservar su defecto. Iterar puntos Unicode, quitar todas las marcas de normalización y extender el extremo original del último carácter normalizado para abarcar marcas combinantes posteriores. `Jose` y `José` sobre `Jose\u0301` deben producir `[0,5)`, tanto en modo completo como parcial, sin acento residual. Backend compara NFD sin marcas y minúsculas; los límites se evalúan en el texto original.
- Repeticiones backend: `_find_positions` usa búsqueda iterativa. Si una candidata no pasa límites, avanzar un punto Unicode desde su inicio; si se acepta, avanzar hasta su final (mantener coincidencias no solapadas automáticas). Caso obligatorio: `Ana Ana; xAna Ana Ana` seleccionando `[0,7)` también encuentra `[14,21)`. Frontend aplica el mismo avance tras rechazar una candidata.
- Límites: evaluar caracteres de token en el texto original a ambos lados del borde; solo rechazar cuando el corte divide un token. Conectores forman token cuando tienen carácter de palabra a ambos lados; `+` inicial seguido de dígito decimal también. Se conservan los errores 422 propios de validación estructural Pydantic; las validaciones semánticas del servicio devuelven 400 y no mutan la sesión.
- Estado EGM: ambos perfiles completados, seis hallazgos Major aceptados mediante PROPOSE FIX (incluidos duplicados vinculados), sin Blockers ni lecturas obligatorias fallidas. Revisión cerrada por la instrucción de una única ronda; no se afirma convergencia. Resolución detallada en `goldfish_review_report.md`.
- Ajuste acotado de fixture adicional: `scripts/test_portable_smoke.py::test_export_utf8_filename` usaba `end=20` para un texto de 17 caracteres. Se cambia únicamente a `len(state.doc_text)` para probar la exportación con un rango válido; no se relaja la protección de rangos del programa.

## Resultado de implementación y validación — 6 de noviembre de 2026

C2, C3, C4 y C5 implementados en `revision-egm`, conservando los cambios anteriores. C1, D1 y C6 comprobados nuevamente. Sin commits, push, publicaciones ni cambios de dependencias.

- C2: contador por acción manual, resolutor compartido entre texto y resaltado, prioridad equivalente en interfaz y sustituciones visibles por aparición. Orden de guardado A→B→A, respuesta demorada con valor repetido y contador de servidor adelantado cubiertos por regresiones. Las solicitudes inválidas comprobadas no alteran la sesión.
- C3: límites Unicode completos por defecto y controles explícitos de parcial en selección y lupa; intervalo seleccionado siempre incluido, incluso dentro de un dato; mapeo de acentos descompuestos y offsets tras emoji corregido.
- C4: origen manual de etiquetas preservado al cambiar categoría en filas y grupos; etiquetas automáticas regeneradas. Las asignaciones explícitas conservan la etiqueta del destino.
- C5: marca de revisión independiente del número de detecciones. Editor y exportación permiten revisión vacía; respetan texto editado y cadena vacía. Carga sin revisión continúa bloqueada; error y cancelación conservan el estado previo.

### Evidencia de regresión y ejecución final

Antes de las correcciones, las regresiones nuevas reprodujeron: C2/C4 **21 fallos, 8 aprobadas**; coincidencias C3 **25 fallos, 12 aprobadas**; exportación vacía C5 **9 fallos, 3 aprobadas**; frontend inicial **5 fallos, 34 aprobadas**. Las pruebas adicionales de atomicidad reprodujeron cuatro fallos y el contador adelantado reprodujo un fallo de vista previa antes de sus respectivos arreglos. Los errores transitorios de integración y fixtures incompletos no se contabilizan como evidencia de defectos del programa.

| Ejecución sobre el código final | Resultado |
| --- | --- |
| `node --test tests/frontend_session.test.cjs` | **45 aprobadas** |
| `.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_browser_manual_review.py` | **1.060 aprobadas, 765 subpruebas aprobadas, 1 omitida y 1 fallo de paquete existente** |
| `ANON_BROWSER_TESTS=1`, pytest `tests/test_browser_manual_review.py`, Edge real instalado | **11 aprobadas**, 49,58 s en la ejecución final |
| Comparación focal de resolución Python/JavaScript | **1.000 casos coincidentes**, incluidos empates, uniones transitivas y offsets Unicode |
| `node --check frontend/app.js` y `git diff --check` | Sin errores de sintaxis ni espacios |

El navegador usa servidor local efímero, archivos DOCX sintéticos, arrastre real sobre el texto y APIs sin mocks. Comprueba cuerpos de solicitudes, controles de parcial, foco/cursor C6, tabla, Anonimizado y editor. **12 DOCX y 12 PDF** descargados se inspeccionan con python-docx/pdfplumber; coinciden con el texto esperado y el enviado desde el editor, incluidas las salidas vacías. Capturas y descargas finales: `build/egm-browser-final-1106/` (artefactos de prueba, no entregables publicados).

Los archivos modificados abarcan `app/models/schemas.py`, servicios `detections`, `clusters`, nuevos `review_state` y `matching`, `app/anonymize/apply.py`, rutas `actions`, `analyze`, `detections`, `entities`, `export`, `app/export/export_utils.py`, los tres archivos de frontend, README y manual. Las regresiones están en los archivos enumerados en la fase D, más `tests/test_review_empty_exports.py` y el ajuste de fixture portátil explicado arriba. El informe original de deriva se conserva.

### Pendiente detectado y posteriormente resuelto

La primera ejecución de `tests/test_package_structure.py::test_launcher_present` falló porque encontró un paquete anterior con `VERSION_APP.txt = 3.4.0` frente al código `APP_VERSION = 3.4.3`. La reconstrucción solicitada después quedó completada y verificada como se detalla abajo. Se conservaron los paquetes anteriores; las pruebas usan `ANON_PKG_DIR` explícito para evaluar la entrega nueva. No quedan comprobaciones de navegador pendientes de C1–C6/D1.

Ambos revisores solicitados completaron la única ronda EGM; las seis observaciones Major justificadas se incorporaron. La fase de revisión está cerrada por la configuración autorizada, sin afirmar convergencia de varias rondas.

## Cierre del portable — 6 de noviembre de 2026

Construido desde los fuentes actuales de `revision-egm`, con Python 3.12.14 de 64 bits y PyInstaller, sin modificar `APP_VERSION` ni reemplazar entregas anteriores:

- Carpeta lista para usar: `dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm/`.
- ZIP: `dist/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip`, **145.420.010 bytes** (138,7 MiB).
- SHA-256: `5154a3a969a73fa488775e6b0a062cad7776ef9d18f08830f856bf90c5bcaf06`, también en el archivo `.zip.sha256` adjunto.
- Carpeta interna del ZIP: `AnonimizadorJudicial-NLP-3.4.3/`; iniciar con `INICIAR.bat` tras extraer todo.

| Verificación actual | Resultado |
| --- | --- |
| Dependencias y auditoría del repositorio | `pip check` sin incompatibilidades; auditoría sin errores |
| Suite general con `ANON_PKG_DIR` nuevo | **1.061 aprobadas, 765 subpruebas aprobadas, 1 omitida**, sin fallos; omisión por enlaces simbólicos de directorio no disponibles en este entorno |
| Estructura del portable y de su copia extraída | **6 aprobadas en cada carpeta**, sin omisiones |
| Lanzador real, reapertura y preservación de otras copias | **7 comprobaciones aprobadas** tanto antes como después de extraer el ZIP |
| Prueba del motor con todas las categorías y exportaciones | **18 comprobaciones aprobadas** en ambas copias; Presidio, spaCy y catálogos disponibles localmente |
| Edge contra el ejecutable compilado | **11 aprobadas**; C1–C6/D1 y **24 descargas** Word/PDF verificadas |
| Datos sensibles desde DOCX/PDF | **6 comprobaciones principales aprobadas** |
| Identidades y carátulas | **48 comprobaciones y 20 casos aprobados** |
| Agrupación/alias y partes Word/cancelación | **46 y 20 comprobaciones aprobadas**; cancelación atendida en 0,328 s |
| ZIP | CRC y SHA-256 válidos; 1.757 entradas; sin sesiones, registros, bases, credenciales ni documentos de prueba; frontend idéntico a los fuentes |

El fixture de `tests/test_browser_manual_review.py` admite ahora `ANON_BROWSER_BASE_URL` local para comprobar el ejecutable real sin iniciar un servidor de desarrollo. Todas las pruebas usaron datos sintéticos. Los dos procesos temporales de esta tarea se cerraron; las copias que ya estaban abiertas permanecieron intactas.

La primera ruta de extracción de prueba resultó demasiado larga para Windows; la extracción completa y el arranque pasaron en `build/xegm/`. Al usar el ZIP conviene extraerlo en una carpeta corta, por ejemplo `C:\Anonimizador`. No se modificaron los archivos del ZIP para sortear esa comprobación.

Evidencia actual: `build/validation/portable_egm_archive_results.json`, `portable_egm_compiled_smoke.json`, `portable_egm_extracted_smoke.json`, `windows_launcher_results.json`, `portable_revision_egm_browser.xml`, carpeta `portable_revision_egm_sensitive/`, `identity_flow_portable.json`, `caption_boundaries_portable.json`, `learned_alias_portable_results.json` y `document_parts_portable.json`. Capturas y descargas del navegador: `build/egm-portable-browser/`.

Empaquetado pendiente resuelto. No se realizaron commits, push ni publicaciones. Se mantiene la limitación de firma digital ya documentada en `docs/DEPLOY.md`; estas pruebas acreditan el funcionamiento en este equipo, no una validación de Control Inteligente de Aplicaciones en otros equipos Windows.
