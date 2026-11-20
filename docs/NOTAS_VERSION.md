# Anonimizador IALAB 3.4.8

Actualización de detección y revisión del 20 de noviembre de 2026.

## Descargar para Windows

[Descargar ZIP completo · 3.4.8](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.8/AnonimizadorJudicial-3.4.8-Windows.zip) · [SHA-256](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.8/AnonimizadorJudicial-3.4.8-Windows.zip.sha256).

Extraé el ZIP en una carpeta nueva y abrí **INICIAR.bat**. El paquete incluye
el ejecutable, la interfaz actualizada, Python, el modelo local y los manuales.
La cabecera y `/health` identifican la versión **3.4.8**.

## Qué cambia

- Abre el navegador recién cuando la aplicación acepta conexiones. Antes podía mostrarse «Se rechazó la conexión» mientras el programa todavía iniciaba.
- Separa las personas enumeradas con coma («Mariela Paz, Hernán Luna») y conserva la forma invertida «APELLIDO, Nombre».
- No toma como persona las frases formadas solo por términos abstractos y corta los nombres en un separador «espacio-guion-espacio».
- Agrega una lista de términos que la detección automática nunca anonimiza, empezando por «Conexidad Subjetiva». Si el término aparece pegado a un nombre, se conserva el nombre.
- Permite desanonimizar un grupo completo, también con una sola variante, y desanonimizar o volver a anonimizar un dato seleccionado en la vista previa.
- Separa el nombre del archivo del aviso de páginas PDF sin texto.
- Rediseña la tabla de Detecciones y agrega un buscador por texto, sustitución, tipo o grupo.

Los PDF de la carpeta **Manuales** son los de la 3.4.6 y no describen estas novedades.

## Verificación y procedencia

El paquete se construye en Windows desde el commit asociado a esta Release.
La publicación automática depende de las pruebas Python/Node, la auditoría,
el inicio real, las comprobaciones de análisis y exportación, la procedencia
del binario y el inicio/análisis del ZIP extraído en otra carpeta.

El ZIP incluye `SOURCE_COMMIT.txt`, `BUILD_PROVENANCE.json`, el inventario de
dependencias y las licencias. Consultá [la verificación de esta entrega](VERIFICACION_3.4.8.md)
y [el historial de cambios](../CHANGELOG.md).

## Uso y límites

Funciona en Windows de 64 bits. No incluye una descarga para macOS y no tiene
firma digital; consultá [el manual de instalación](MANUAL_INSTALACION.md)
si Windows impide abrirlo. Requiere DOCX o PDF con texto seleccionable, sin OCR.

El procesamiento se realiza en tu equipo. Revisá el resultado antes de
compartirlo: las exportaciones reconstruyen el texto y la tabla CSV de
equivalencias contiene los datos originales.
