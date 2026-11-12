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

La verificación funcional, visual y del paquete IALAB se registra durante
la preparación de esta edición. El portable está pendiente de construcción,
verificación y publicación. Antes de anunciar una descarga se deben completar
los controles de [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

El archivo previsto es `AnonimizadorJudicial-3.4.4-Windows.zip`, acompañado
de su SHA-256. No se reutiliza como entrega IALAB un ejecutable anterior con
recursos MPF.

## Límites

La detección requiere DOCX o PDF con texto seleccionable; no incluye OCR.
Las pruebas usan documentos ficticios y no sustituyen la revisión humana.
El CSV de equivalencias contiene los datos originales. El portable Windows
no tiene firma digital y no funciona en macOS.
