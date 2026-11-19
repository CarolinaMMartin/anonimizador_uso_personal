# Anonimizador IALAB 3.4.7

Paquete nuevo de Windows del 19 de noviembre de 2026. Reemplaza a la 3.4.6, cuya descarga bloqueaba Microsoft Defender, y conserva sus mejoras de revisión manual, lectura de PDF y documentación.

## Descargar para Windows

[Descargar ZIP completo · 3.4.7](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.7/AnonimizadorJudicial-3.4.7-Windows.zip) · [SHA-256](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.7/AnonimizadorJudicial-3.4.7-Windows.zip.sha256).

Extraé el ZIP en una carpeta nueva y abrí **INICIAR.bat**. El paquete incluye
el ejecutable, la interfaz actualizada, Python, el modelo local y los manuales.
La cabecera y `/health` identifican la versión **3.4.7**.

## Qué cambia

- Publica el programa de la 3.4.6 en un ZIP nuevo. La lógica de anonimización, la interfaz y los manuales son los mismos.
- Conserva las decisiones manuales si repetís el análisis con las mismas categorías. Si las cambiás después de revisar, pide confirmación antes de reemplazar la revisión.
- Identifica las páginas del PDF que quedaron sin texto recuperable y pide confirmación antes de exportar solo el texto disponible.
- Reúne letras y acentos separados en la capa de texto del PDF y mejora la representación de letras en la exportación. Conserva símbolos legítimos como ° y ®.
- Incluye el manual de usuario, el manual técnico y el resumen ejecutivo con la identidad visual del IALAB en la carpeta **Manuales** del ZIP.

Si un PDF muestra una letra pero entrega otro carácter al copiar su texto, usá el documento fuente o una copia con OCR y comprobá el resultado en ambas vistas.

## Verificación y procedencia

El paquete se construye en Windows desde el commit asociado a esta Release.
La publicación automática depende de las pruebas Python/Node, la auditoría,
el inicio real, las comprobaciones de análisis y exportación, la procedencia
del binario y el inicio/análisis del ZIP extraído en otra carpeta.

El ZIP incluye `SOURCE_COMMIT.txt`, `BUILD_PROVENANCE.json`, el inventario de
dependencias y las licencias. Consultá [la verificación de esta entrega](VERIFICACION_3.4.7.md)
y [el historial de cambios](../CHANGELOG.md).

## Uso y límites

Funciona en Windows de 64 bits. No incluye una descarga para macOS y no tiene
firma digital; consultá [el manual de instalación](MANUAL_INSTALACION.md)
si Windows impide abrirlo. Requiere DOCX o PDF con texto seleccionable, sin OCR.

El procesamiento se realiza en tu equipo. Revisá el resultado antes de
compartirlo: las exportaciones reconstruyen el texto y la tabla CSV de
equivalencias contiene los datos originales.
