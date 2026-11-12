# Verificación de 3.4.4 · Edición IALAB

Esta copia se prepara el **12 de noviembre de 2026**, desde el commit de origen
`a293199` de la edición MPF. La versión funcional se conserva en **3.4.4**;
la interfaz y la documentación identifican la edición **IALAB**.

El código se mantiene en `CarolinaMMartin/anonimizador_uso_personal`.
La carpeta original y su configuración Git permanecen separadas.

## Alcance

Se reemplaza la identidad visual por el manual `marca-ialab-v2`: logos,
isotipo, favicon, paleta y Roboto local. Se conservan las funciones de
detección, revisión, agrupación y exportación de la versión de origen.

Los resultados anteriores del MPF se conservan en
[su verificación histórica](historico/VERIFICACION_MPF_3.4.4.md); no se
presentan como comprobaciones del código ni del ejecutable de esta copia.

## Estado de comprobación

Comprobaciones realizadas sobre la copia IALAB con Python 3.12.14:

- Suite funcional: **1.091 pruebas y 765 subtests aprobados**; 18 pruebas
  omitidas antes de disponer del portable o por requerir ejecución opcional.
- Frontend: **45 pruebas aprobadas** con Node.
- Navegador real (Edge): **11 pruebas aprobadas**, incluidas selección manual,
  superposiciones, grupos, búsqueda y descargas Word/PDF con contenido verificado.
- Auditoría del repositorio y `pip check`: sin errores.
- Revisión visual de las capturas de carga, revisión y editor generadas por
  las pruebas: logos, Roboto local y paleta IALAB visibles, sin solapamientos.
  El control manual del navegador no estuvo disponible por una limitación
  de identificación de URL; se revisaron las capturas de las pruebas.
- CI del [commit de identidad IALAB](https://github.com/CarolinaMMartin/anonimizador_uso_personal/commit/1d4a130d24dd18e1747c5c15cdccb3bb893aea8d):
  aprobada en Windows y Linux con Python 3.12 y 3.13
  ([ejecución](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/runs/43247973059)).

El portable se construyó de forma independiente en
`dist/AnonimizadorJudicial-NLP/`, con los fuentes y recursos de esta edición.
Las comprobaciones adicionales aprobaron:

- Estructura del paquete: **6 pruebas**, sin omisiones.
- Arranque Windows: **7 controles**, incluidos doble apertura, reutilización
  de la instancia y conservación de la sesión. La copia anterior abierta
  continuó funcionando; IALAB eligió otro puerto libre.
- Detección con todas las categorías y con Personas; agrupación de variantes;
  partes de documentos Word/PDF; identificadores sensibles y revisión manual.
- Identidades y exportaciones Word/PDF; **20 casos** de carátulas y prosa.
- Coincidencia de los recursos servidos con los logos, isotipo, Roboto y licencia
  de esta copia. Procedencia del ejecutable e inventarios verificados por el constructor.

El inventario `docs/dependencies-frozen.txt` se copió del build final.
Los controles de entrega siguen [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

El archivo de entrega es `AnonimizadorJudicial-3.4.4-Windows.zip`, acompañado
de su SHA-256. No se reutiliza como entrega IALAB un ejecutable anterior con
recursos MPF.

## Límites

La detección requiere DOCX o PDF con texto seleccionable; no incluye OCR.
Las pruebas usan documentos ficticios y no sustituyen la revisión humana.
El CSV de equivalencias contiene los datos originales. El portable Windows
no tiene firma digital y no funciona en macOS.
