# Anonimizador de documentos · IALAB

<img src="frontend/assets/ialab/logo_azul.png" alt="IALAB · Facultad de Derecho, Universidad de Buenos Aires" width="240">

**Ocultá datos personales de un documento antes de compartirlo.**
La aplicación reemplaza nombres, documentos, teléfonos, domicilios y otros datos
por etiquetas como **[PERSONA_1]**. Vos revisás el resultado y lo descargás.
Es gratuita y trabaja en tu computadora, sin enviar tus documentos a Internet.

## Edición IALAB — 3.4.4

Esta copia independiente conserva las mejoras funcionales de la versión 3.4.4
y aplica la identidad de **IALAB — Facultad de Derecho, UBA**. El proyecto y
las descargas de esta edición se mantienen en **anonimizador_uso_personal**.
La copia original del MPF se conserva por separado.

## Descargar para Windows · IALAB 3.4.4

El paquete **AnonimizadorJudicial-3.4.4-Windows.zip** corresponde a esta
edición IALAB y conserva las mejoras funcionales de la versión 3.4.4.
Incluye el ejecutable, el modelo local, la interfaz y los manuales.

[**Descargar para Windows · 3.4.4**](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.4/AnonimizadorJudicial-3.4.4-Windows.zip) ·
[Archivo SHA-256](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.4/AnonimizadorJudicial-3.4.4-Windows.zip.sha256)

Descargá el ZIP completo para **Windows 10 y 11 de
64 bits**, elegí **Extraer todo** y abrí **INICIAR.bat** desde la carpeta
extraída. El portable incluye Python y el modelo local; conservá toda la carpeta.
**Code → Download ZIP** contiene el código fuente y no incluye el ejecutable.

[Estado de verificación](docs/VERIFICACION_3.4.4.md) ·
[Ayuda para abrir la aplicación](docs/MANUAL_INSTALACION.md)

Todavía no hay un paquete IALAB actualizado para macOS. El ZIP Windows no
funciona en Mac ni celulares. La entrega no tiene firma digital; si Windows
impide abrirla, consultá [el aviso de instalación](docs/MANUAL_INSTALACION.md#si-windows-bloquea-la-aplicación).

## Anonimizar un documento

1. **Cargá el archivo:** un Word **.docx** o un **PDF donde puedas seleccionar
   el texto**, de hasta 40 MB.
2. **Elegí los datos que querés ocultar** y hacé clic en **Analizar documento**.
3. **Revisá los resultados:** cada fila muestra el dato original y la etiqueta
   que lo reemplazará. Desmarcá lo que quieras conservar.
4. **Agregá lo que falte:** en la vista **Original**, seleccioná el texto,
   elegí su categoría y hacé clic en **Solo anonimizar**. Esto también oculta
   sus repeticiones iguales que formen un dato completo. Para buscar otras
   apariciones, usá la lupa.
5. **Comprobá el resultado** en la vista **Anonimizado**. Después, hacé clic
   en **Abrir editor y verificar**, revisá el texto y descargá el Word o PDF.

**Revisá siempre el archivo descargado antes de compartirlo.** La detección
puede omitir datos o marcar algo que quieras conservar.

La selección que hacés se respeta exactamente, incluso dentro de una palabra.
La casilla **Permitir coincidencias parciales** de la selección afecta sus
repeticiones; la misma opción en la lupa permite buscar dentro de palabras o
datos compuestos. Está desactivada por defecto: buscar `Ana` no incluye
`Mariana` ni `Ana@example.test`. La lupa ignora mayúsculas y tildes.

Si dos datos activos se superponen, se oculta toda la zona cubierta y se usa
la etiqueta de la última decisión manual. Las demás apariciones conservan sus
etiquetas. Cuando hay diferencias, junto al campo editable se muestran las
sustituciones aplicadas. Cambiar el tipo de dato conserva las etiquetas que
escribiste; asignarlo a otro grupo usa la etiqueta de ese grupo.

Después de analizar, podés abrir el editor y descargar Word o PDF aunque no
haya detecciones o hayas eliminado todas. Cargar un archivo por sí solo no
completa la revisión. Las correcciones del editor, incluso dejarlo vacío, se
respetan al descargar.

## Si algo no funciona

| Qué sucede | Qué hacer |
| --- | --- |
| No encuentro INICIAR | Extraé el ZIP completo mediante **Extraer todo**. Luego abrí la carpeta `AnonimizadorJudicial-NLP-3.4.4` que está dentro. |
| Windows dice «Control Inteligente de Aplicaciones ha bloqueado un archivo» | [Leé esta indicación](docs/MANUAL_INSTALACION.md#si-windows-bloquea-la-aplicación). Esta versión aún no está firmada para esos equipos. |
| No se abre el navegador | Esperá el inicio y copiá en el navegador la dirección que muestra la ventana. También podés abrir **VERIFICAR.bat** en esa misma carpeta. |
| El PDF es un escaneo o una foto | Necesitás una copia con texto seleccionable. La aplicación no lee el texto dentro de imágenes. |
| Falta ocultar un dato | Seleccionalo en **Original**, elegí su categoría y pulsá **Solo anonimizar**. Comprobá que su fila esté marcada. |
| Cambié la revisión después de abrir el editor | Volvé a **Abrir editor y verificar** para actualizar el resultado antes de descargarlo. |
| El documento sale con otro formato | Es esperable: se genera un documento nuevo con el texto revisado. No se conserva la distribución original de tablas, imágenes y páginas. |

## Actualizar una versión anterior

Guardá primero tus resultados y extraé el ZIP de esta entrega **en una carpeta
nueva**. Abrí **INICIAR** desde esa carpeta;
los accesos directos anteriores siguen abriendo la versión anterior.
El número de versión aparece en la parte superior de la aplicación.

Si usabas 3.4.3 o una versión anterior, verificá que la nueva copia indique
**v3.4.4**. Esta actualización conserva la detección de nombres en carátulas,
las sugerencias de identidad y las decisiones manuales. La cabecera identifica
la edición IALAB y utiliza su manual de marca.
[Ver las novedades](docs/NOTAS_VERSION.md).

## Tus documentos y tu privacidad

Los documentos se procesan en tu equipo. Guardá tus resultados antes de cerrar
la aplicación: el trabajo en curso se pierde al cerrar por completo la aplicación.
Cerrar solo la pestaña del navegador puede dejar la aplicación funcionando.

Si descargás la **tabla de equivalencias (CSV)**, ese archivo contiene los
**datos originales** junto a sus etiquetas. Guardalo de forma privada y
compartí el documento anonimizado que revisaste.

## Abrir desde el código fuente

Para trabajar con el código fuente, seguí las
[instrucciones de desarrollo](docs/DESARROLLO.md) para preparar Python,
instalar las dependencias y el modelo local, y ejecutar
**INICIAR_DESARROLLO.bat** en Windows. La preparación inicial requiere Internet;
el procesamiento de documentos funciona localmente.

## Más ayuda

[Manual de uso](docs/MANUAL_USUARIO.md) · [Ayuda para abrir la aplicación](docs/MANUAL_INSTALACION.md)

El portable es para Windows. **No funciona en Mac ni en celulares.**

Desarrollado por **IALAB — Laboratorio de Innovación e Inteligencia Artificial,
Facultad de Derecho, Universidad de Buenos Aires**. Uso personal y académico.
Identidad visual aplicada a partir del paquete de marca IALAB suministrado.
[Manual y criterios de aplicación](docs/marca/README.md).

[Información para quienes desarrollan](docs/DESARROLLO.md) ·
[Licencia de uso](LICENSE) · [Créditos y componentes](THIRD_PARTY_NOTICES.txt) ·
[Aviso sobre marcas](NOTICE) · [Informar un problema de seguridad](SECURITY.md)
