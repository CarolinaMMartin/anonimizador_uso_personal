# Anonimizador IALAB 3.4.9

Corrección de la revisión de documentos largos del 27 de noviembre de 2026.

## Descargar para Windows

[Descargar ZIP completo · 3.4.9](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.9/AnonimizadorJudicial-3.4.9-Windows.zip) · [SHA-256](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.9/AnonimizadorJudicial-3.4.9-Windows.zip.sha256).

Extraé el ZIP en una carpeta nueva y abrí **INICIAR.bat**. El paquete incluye
el ejecutable, la interfaz actualizada, Python, el modelo local y los manuales.
La cabecera y `/health` identifican la versión **3.4.9**.

## Qué cambia

- Corrige la lentitud al revisar documentos largos. Quitar una variante, confirmar, rechazar o unir un grupo podía tardar minutos. En un documento ficticio de 400.000 caracteres y 1.866 apariciones, medido en Chrome, quitar una variante pasó de 161 s a 0,4 s.
- Deja de pedir el documento después de cada acción de revisión. La vista previa se redibuja con los reemplazos que devuelve cada acción.
- Calcula la nota «Aplicado por aparición» sin comparar cada aparición con todas las demás.
- La aplicación ya no se vuelve más lenta a medida que avanza la revisión: los desplegables de grupos comparten un único control de cierre.
- La detección, los grupos sugeridos y las exportaciones son los de la 3.4.8.

Desanonimizar un grupo todavía guarda una variante por vez; en un grupo con muchas variantes puede tardar algunos segundos.

Los PDF de la carpeta **Manuales** son los de la 3.4.6 y no describen estas novedades.

## Verificación y procedencia

El paquete se construye en Windows desde el commit asociado a esta Release.
La publicación automática depende de las pruebas Python/Node, la auditoría,
el inicio real, las comprobaciones de análisis y exportación, la procedencia
del binario y el inicio/análisis del ZIP extraído en otra carpeta.

El ZIP incluye `SOURCE_COMMIT.txt`, `BUILD_PROVENANCE.json`, el inventario de
dependencias y las licencias. Consultá [la verificación de esta entrega](VERIFICACION_3.4.9.md)
y [el historial de cambios](../CHANGELOG.md).

## Uso y límites

Funciona en Windows de 64 bits. No incluye una descarga para macOS y no tiene
firma digital; consultá [el manual de instalación](MANUAL_INSTALACION.md)
si Windows impide abrirlo. Requiere DOCX o PDF con texto seleccionable, sin OCR.

El procesamiento se realiza en tu equipo. Revisá el resultado antes de
compartirlo: las exportaciones reconstruyen el texto y la tabla CSV de
equivalencias contiene los datos originales.
