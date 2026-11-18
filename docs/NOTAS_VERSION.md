# Anonimizador IALAB 3.4.5

Actualización de estética del 18 de noviembre de 2026.

## Descargar para Windows

[Descargar ZIP completo · 3.4.5](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.5/AnonimizadorJudicial-3.4.5-Windows.zip) · [SHA-256](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.5/AnonimizadorJudicial-3.4.5-Windows.zip.sha256).

Extraé el ZIP en una carpeta nueva y abrí **INICIAR.bat**. El paquete incluye
el ejecutable, la interfaz actualizada, Python, el modelo local y los manuales.
La cabecera y `/health` identifican la versión **3.4.5**.

## Qué cambia

- Encabezado blanco con logo azul del IALAB.
- Paneles redondeados, bordes sutiles y más espacio entre elementos.
- Botones principales redondeados con acentos violeta del laboratorio.
- Información de formatos sobre fondo gris neutro.
- Ajustes de distribución en pantallas pequeñas.

Se conservan las funciones de detección, revisión manual, agrupación y
exportación Word/PDF/CSV de 3.4.4. El cambio de estética también se incluye
en el ZIP descargable; no requiere editar archivos de una instalación anterior.

## Verificación y procedencia

El paquete se construye en Windows desde el commit asociado a esta Release.
La publicación automática depende de las pruebas Python/Node, la auditoría,
el inicio real, las comprobaciones de análisis y exportación, la procedencia
del binario y el inicio/análisis del ZIP extraído en otra carpeta.

El ZIP incluye `SOURCE_COMMIT.txt`, `BUILD_PROVENANCE.json`, el inventario de
dependencias y las licencias. Consultá [la verificación de esta entrega](VERIFICACION_3.4.5.md)
y [el historial de cambios](../CHANGELOG.md).

## Uso y límites

Funciona en Windows de 64 bits. No incluye una descarga para macOS y no tiene
firma digital; consultá [el manual de instalación](MANUAL_INSTALACION.md)
si Windows impide abrirlo. Requiere DOCX o PDF con texto seleccionable, sin OCR.

El procesamiento se realiza en tu equipo. Revisá el resultado antes de
compartirlo: las exportaciones reconstruyen el texto y la tabla CSV de
equivalencias contiene los datos originales.
