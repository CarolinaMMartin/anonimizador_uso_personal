# Revisión acotada de deriva — Anonimizador Judicial

> Informe histórico anterior a las correcciones EGM. Sus hallazgos y pruebas
> pendientes describen el estado revisado, no el de la descarga vigente.
> Ver [el cierre de correcciones](docs/revision-egm/correcciones_pendientes.md)
> y el [README](README.md).

Fecha: 2026-11-06. Referencia del repositorio: `628913f6803eb6677fefdd0fbd3a35a28f4709cf`.

Recorrido revisado: **selección manual → aplicación de la anonimización → editor → exportación a Word y PDF**. Referencias iniciales: `README.md` y `docs/MANUAL_USUARIO.md`, que describen la entrega 3.4.3. Se contrastó el código fuente del repositorio; no se verificó su correspondencia con el ejecutable distribuido.

Revisión EGM de lectura estática. **No se ejecutaron la aplicación ni pruebas, ni se modificaron código o documentación existente.** Los resultados de los ejemplos se deducen del código; no son resultados observados. Los informes `VERIFICACION_*` se consideran antecedentes y no se utilizan como evidencia de que las pruebas sigan pasando. Leer una prueba existente tampoco acredita su resultado actual.

Se registran **seis hallazgos sustentados por lectura**: tres desajustes de aplicación o visualización y tres restricciones o ambigüedades documentales. Se separa **una duda de integración que requiere ejecutar el navegador**. “Confirmado” refiere a la condición identificada en el código, no a una reproducción realizada. Las pruebas propuestas usan datos sintéticos y quedan pendientes. Los hallazgos compartidos por ambos documentos se describen una sola vez.

## README.md

- **C1 · Confirmado por lectura · Prioridad alta: la búsqueda de repeticiones puede dejar parcialmente visible la selección confirmada.**

  **Esperado:** `README.md:47–49` indica seleccionar un texto para ocultarlo junto con sus repeticiones. `docs/MANUAL_USUARIO.md:125–128` explicita que se respeta la selección confirmada.

  **Implementado y evidencia:** `_find_positions`, en `app/services/detections.py:14–18`, usa `re.finditer`, con coincidencias no solapadas. `add_manual_detection`, en ese archivo, líneas 44–47, utiliza esos resultados y solo conserva el rango solicitado si la búsqueda queda vacía. No garantiza añadir el intervalo que eligió el usuario. Para texto `121212`, seleccionar los últimos cuatro caracteres, rango `[2,6)`, produce únicamente la posición `[0,4)`. `anonymize_text` (`app/anonymize/apply.py:15–30`) deduce entonces `[DATO_1]12` en modo categorizado y categoría `OTRO`.

  **Impacto:** permanecen visibles dos caracteres de la selección confirmada. El resultado llega al editor por `_anonymized_preview_text`/`export_preview` (`app/api/routes_export.py:28–44`) y, si no se corrige allí, a ambos archivos mediante los manejadores `exportDocx`/`exportPdf` (`frontend/app.js:1563–1582`). Es un desajuste de cobertura de la selección, anterior a la exportación.

  **Prueba concreta pendiente:** cargar un documento sintético con `121212`, eliminar detecciones previas sobre ese texto y seleccionar exactamente sus cuatro últimos caracteres como **Otros → Solo anonimizar**. Inspeccionar las posiciones guardadas y comprobar que cubren todo `[2,6)`. Comparar Anonimizado, editor, Word y PDF. El criterio mínimo es que no sobreviva ningún carácter de ese intervalo; ocultar la unión de ambas coincidencias también lo satisface.

- **C2 · Confirmado por lectura · Prioridad media: dos detecciones sobre el mismo fragmento no respetan necesariamente la etiqueta de la selección manual.**

  **Esperado:** `README.md:45–49` dice que cada fila muestra la etiqueta que reemplazará el dato y permite elegir la categoría de una selección. El manual, líneas 125–132, refuerza ese recorrido y la conservación del tipo al exportar.

  **Implementado y evidencia:** `add_manual_detection` (`app/services/detections.py:60–97`) reutiliza una fila solo si coinciden categoría y texto normalizado. Seleccionar un fragmento existente con otra categoría crea una segunda fila activa. `refresh_suggestions` (`app/services/suggestions.py:59–65`) no resuelve esos rangos. `anonymize_text` (`app/anonymize/apply.py:18–25`) fusiona intervalos solapados y conserva la etiqueta del primero, ordenando por inicio y mayor extensión. En rangos idénticos prevalece el orden previo; no hay prioridad manual. `mergeOverlappingRanges` y `renderPreviewLocal` (`frontend/app.js:1330–1340, 1402–1423`) repiten esa regla en la vista.

  **Impacto:** el fragmento queda oculto, pero una fila puede mostrar `[EMPRESA_1]` mientras el resultado conserva `[PERSONA_1]`. Puede atribuirse una categoría o identidad distinta de la elegida. La discrepancia está entre las decisiones mostradas y su aplicación; no implica una reclasificación realizada por Word/PDF.

  **Prueba concreta pendiente:** sin otras detecciones, agregar manualmente `Acme` como Persona y después seleccionar el mismo texto como Empresa, dejando ambas filas activas. Comparar etiquetas de las filas, Anonimizado, editor y ambos archivos. Repetir con un rango contenido en otro. Debe definirse qué selección prevalece o cómo se comunica el conflicto: la documentación actual no establece esa excepción.

- **C3 · Conducta confirmada; ambigüedad documental · Prioridad media: “repeticiones iguales” incluye fragmentos dentro de otras palabras.**

  **Esperado:** `README.md:47–49` y `docs/MANUAL_USUARIO.md:127–128` hablan de repeticiones iguales, sin precisar si deben ser palabras o datos completos. No hay base suficiente para imponer límites de palabra como requisito definitivo.

  **Implementado y evidencia:** `_find_positions` (`app/services/detections.py:14–18`) busca subcadenas literales sin límites de palabra y sin distinguir mayúsculas. Seleccionar `Ana` en `Ana y Mariana` también selecciona el final de `Mariana`. La lupa comparte esa ausencia de límites en `searchTool.computeMatches` (`frontend/app.js:1913–1925`).

  **Impacto:** se puede modificar texto que el usuario no considera otra aparición del dato; por ejemplo, obtener `[PERSONA_1] y Mari[PERSONA_1]`. Todas esas posiciones integran la misma fila y su activación se controla en conjunto.

  **Prueba concreta pendiente:** usar ese texto sin otras detecciones, seleccionar `Ana` y revisar el contador de apariciones, Anonimizado, editor, Word y PDF. Registrar si se espera anonimizar también el fragmento de `Mariana`. Si la búsqueda por subcadenas es deliberada, corresponde precisar la documentación; el comportamiento por sí solo no demuestra un error del programa.

## docs/MANUAL_USUARIO.md

- **C4 · Confirmado por lectura; excepción documental omitida · Prioridad media: cambiar el tipo de una fila reemplaza su etiqueta personalizada.**

  **Esperado:** las líneas 140–143 incluyen el cambio de tipo entre las operaciones tras las cuales se conservan las etiquetas personalizadas. La redacción no excluye la etiqueta de la fila reclasificada.

  **Implementado y evidencia:** el manejador `.cat-select` de `renderTable` (`frontend/app.js:853–857`) envía únicamente `cat`. `patch_detection` (`app/api/routes_detections.py:54–69`) lo pasa a `update_detection`. Esta función genera otra etiqueta al cambiar la categoría y la asigna cuando `placeholder is None`, aunque la anterior fuera manual (`app/services/detections.py:239–254`). En una fila independiente con `[RESERVADO]`, cambiar a Empresa genera una etiqueta de esa categoría. La actualización posterior de sugerencias no restaura la anterior.

  **Impacto:** se pierde una denominación elegida durante la revisión y el resultado regenerado para Word/PDF utiliza la nueva. No se observa una pérdida causada por el exportador.

  **Prueba concreta pendiente:** agregar una detección manual independiente, editar su etiqueta a `[RESERVADO]`, esperar el guardado y cambiar su tipo a Empresa. Comparar etiqueta, Anonimizado, editor y ambos archivos. Si regenerar la etiqueta es la decisión buscada, la documentación debe distinguir esa operación de conservar las etiquetas de las demás filas; no corresponde asumir que toda regeneración es un defecto.

- **C5 · Confirmado por lectura; restricción no documentada · Prioridad media: eliminar la última detección bloquea el editor y Word/PDF.**

  **Esperado:** el manual permite eliminar detecciones (línea 140) y luego revisar y exportar (153–156), sin indicar que deba conservarse al menos una. `README.md:50–51` tampoco menciona ese requisito.

  **Implementado y evidencia:** `export_preview` (`app/api/routes_export.py:37–42`), `export_docx` (58–63) y `export_pdf` (85–90) rechazan `state.detections` vacío con HTTP 400 y el mensaje «No hay detecciones. Analizá el documento primero». El control precede a `resolve_export_text` (`app/export/export_utils.py:22–28`), de modo que los endpoints Word/PDF también bloquean una petición que ya incluya texto revisado. `remove_detection` (`app/services/detections.py:214–222`) sí permite que la lista quede vacía.

  **Impacto:** después de eliminar el último falso positivo o una selección manual innecesaria, el usuario no puede continuar y recibe una indicación de analizar aunque ya lo haya hecho. Desactivar todas las filas no vacía esa lista; eliminar y desactivar tienen consecuencias distintas no explicadas en este paso.

  **Prueba concreta pendiente:** analizar un documento, agregar una detección manual si hace falta y eliminar todas las filas. Intentar abrir el editor. Verificar también las dos rutas de exportación con una sesión válida y un campo `text` sintético. Contrastar con el mismo caso dejando una fila desactivada. El bloqueo es inequívoco en el código; queda por decidir si se mantiene como restricción documentada o se cambia el flujo.

- **C6 · Confirmado por lectura del flujo; reproducción visual pendiente · Prioridad media: editar la etiqueta desde una fila de un grupo puede dejar la vista Anonimizado desactualizada.**

  **Esperado:** las líneas 119–122 describen una etiqueta común para las variantes del grupo y la comparación en la vista previa; `README.md:50–51` pide verificar Anonimizado antes de abrir el editor.

  **Implementado y evidencia:** al editar la etiqueta desde **Detecciones**, el manejador `.placeholder-input` modifica solo esa fila local y renderiza inmediatamente la vista (`frontend/app.js:845–851`). `startPendingSave` llama a `saveDetectionPatch` sin `refresh:true` (714–720). El servidor propaga la etiqueta a todas las variantes confirmadas mediante `update_detection` (`app/services/detections.py:262–268`) y `_sync_cluster_to_detections` (`app/services/clusters.py:30–38`). La respuesta actualiza las detecciones en memoria, pero `saveDetectionPatch` solo redibuja tabla y vista si `refresh` está activo (`frontend/app.js:684–690`). `openEditorPanel`, en cambio, pide el texto actualizado al servidor (1514–1523).

  **Impacto:** otras filas y sus apariciones ya dibujadas pueden seguir mostrando etiquetas anteriores mientras el editor y la exportación utilizan las nuevas. El contenido sensible sigue oculto, pero la comprobación visual puede presentar identidades distintas de las que se descargan. El caso corresponde a editar desde una fila, no desde el control de etiqueta del grupo.

  **Prueba concreta pendiente:** crear y confirmar un grupo con dos variantes, mostrar Anonimizado y cambiar la etiqueta de una variante desde la tabla. Esperar a que termine el PATCH sin cambiar de vista. Comparar ambas filas y apariciones con la respuesta del servidor; después abrir el editor y exportar Word/PDF. Repetir tras cambiar de vista para identificar cuándo se corrige el dibujo. La falta de actualización está identificada en el flujo; su manifestación visual no se observó en esta revisión.

- **D1 · Duda que requiere ejecutar la aplicación · Prioridad alta si se reproduce: una selección con espacios múltiples podría desplazarse a otra aparición cercana.**

  **Esperado:** las líneas 125–128 prometen respetar la selección confirmada, aunque no la reconozca el análisis automático.

  **Indicio en el código:** `getSelectionInPreview` (`frontend/app.js:1698–1733`) reduce los espacios de `Selection.toString()` a uno (1711), pero compara ese valor con un fragmento del documento sin esa normalización (1716, 1724). Si difieren, busca desde 40 caracteres antes y sustituye los límites por la primera coincidencia (1725–1729). `runManualDetectionAndMaybeGroup` envía esos límites al servidor (1794–1796). Para `Ana Ruiz; Ana  Ruiz`, la selección de la segunda aparición podría reubicarse en la primera. `_find_positions` (`app/services/detections.py:14–18`) no equipara un espacio con dos, por lo que esa selección original podría quedar visible.

  **Impacto posible:** ocultar una aparición distinta de la elegida y trasladar el dato restante al editor y a Word/PDF. La barra muestra el texto normalizado y podría no hacer evidente el desplazamiento.

  **Qué falta confirmar:** la captura real del rango y el texto devuelto por el navegador con los resaltados presentes. `tests/frontend_session.test.cjs:33, 56–59` simula `getSelection()` e inyecta directamente `pendingSelection`; su lectura no demuestra el comportamiento de la selección real ni un resultado vigente de las pruebas.

  **Prueba concreta pendiente:** cargar un DOCX sintético con las dos apariciones, eliminar detecciones previas y arrastrar sobre la segunda, conservando su doble espacio. Comprobar el rango enviado, la fila agregada, Anonimizado, editor y ambos archivos. Repetir con salto de línea y tabulación. Solo una ejecución del recorrido permitirá confirmar o descartar este problema de integración; por ahora no se informa como fallo reproducido.
