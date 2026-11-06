# Manual de usuario — Anonimizador Judicial 3.4.3

Herramienta académica de uso personal desarrollada por IALAB, con identidad
visual del Ministerio Público Fiscal de la Ciudad Autónoma de Buenos Aires
adaptada a partir de los recursos suministrados para esta entrega.

---

## 1. Qué hace esta herramienta

**Detección automatizada de datos personales.** Controlá, editá y luego
descargá el documento anonimizado.

La anonimización se realiza **localmente en tu equipo**. No se envían
datos ni información a servidores externos.

Detecta automáticamente, entre otros:

- Personas, DNI y CUIT/CUIL.
- Emails, teléfonos y domicilios.
- Empresas y organismos judiciales.
- Patentes, expedientes, números de seguimiento de denuncias y enlaces.
- Pólizas de seguro, números de chasis y motor.

Reemplaza cada dato por una etiqueta, por ejemplo `[PERSONA_1]` o
`[DNI_1]`, y permite exportar Word, PDF, CSV y Markdown.
Los identificadores sin categoría específica, como seguimiento, póliza,
chasis o motor, se muestran en **Otros** y se reemplazan por `[DATO_1]`.

---

## 2. Cómo iniciar

### Windows

1. Doble clic en **`INICIAR.bat`**.
2. Se abre la dirección local indicada al iniciar, normalmente <http://127.0.0.1:8787>.
   Si el puerto está ocupado, usa otro libre entre 8788 y 8796.
3. Verificá **v3.4.3** en el indicador superior.

Repetir `INICIAR.bat` abre la instancia existente de esa carpeta. No cierra las
otras copias ni transfiere sus documentos.

### macOS

La entrega 3.4.3 se verifica en Windows. Los paquetes anteriores de macOS
conservan su propia versión y sus instrucciones. Este ZIP Windows no funciona
en Mac; una compilación nueva debe probarse en ese sistema antes de publicarse.

El indicador superior debe mostrar algo similar a:

```text
100% local vX.Y.Z · Presidio · spaCy · Catálogos cargados
```

`vX.Y.Z` es la versión instalada. Esta entrega es **3.4.3**.
Sus cambios figuran en `CHANGELOG.md` incluido en el paquete.

---

## 3. Flujo de trabajo

### Paso 1 — Cargar documento

- Formatos: **Word (.docx)** o **PDF digital** con texto seleccionable.
- Arrastrá el archivo o hacé clic en la zona de carga.
- No se procesan PDFs completamente escaneados.
- Límite: **40 MB**. Word extrae párrafos, tablas, encabezados y pies; verificá
  por separado contenido de imágenes, dibujos, notas y revisiones pendientes.

**Consejo:** si el PDF es una imagen, convertilo antes a Word o a PDF con
capa de texto.

### Paso 2 — Configurar y analizar

- **Modo categorizado:** `[PERSONA_1]`, `[DNI_1]`.
- **Modo genérico:** `[NOMBRE]`, `[DNI]`.
- **Modo iniciales:** reemplaza nombres por iniciales.
- Marcá las categorías que querés buscar.
- Conservá **Otros** activada para incluir seguimiento de denuncias, pólizas,
  chasis, motor y enlaces.
- Hacé clic en **Analizar documento**.
- Seleccioná al menos una categoría. **Detener** solicita la cancelación;
  el motor la atiende al llegar a un punto de control entre sus bloques.

Un catálogo de personas faltante, vacío o inválido detiene el análisis y
conserva la revisión anterior. Reiniciá la aplicación después de corregir o
restaurar sus recursos.

### Paso 3 — Revisar

La revisión tiene dos pestañas:

- **Detecciones:** permite activar, desactivar, cambiar tipo, editar o unir
  hallazgos.
- **Identidades o grupos:** reúne variantes que podrían corresponder al
  mismo dato.

Revisá las variantes y usá **Confirmar grupo** para que todas reciban la
misma etiqueta. **Unir similares** confirma las variantes propuestas para
esa identidad; **Ignorar similares** desmarca esas filas.

Si un nombre o apellido corto puede corresponder a varias personas, queda
separado. Podés asignarlo manualmente después de revisar el contexto.
El análisis también busca referencias cortas a partir de los nombres completos
que detectó en ese documento, aunque el apellido no esté en el catálogo.
También busca repeticiones de identificadores previamente etiquetados y de
razones sociales completas. No agrupa documentos, teléfonos ni patentes
distintos por parecerse entre sí.
En las carátulas judiciales, «c/» separa las partes y «s/» introduce el asunto.
El nombre anterior no debe absorber a la otra persona ni al asunto. Revisá
cada parte por separado antes de confirmar sus variantes.
En esos campos también se detectan nombres escritos en minúsculas y
apellidos fuera del catálogo, incluso si aparece solo uno de los separadores.
Las empresas y los organismos conservan su categoría; un título de documento
o trámite seguido de «s/» no se trata como un nombre de persona.
Para aplicar esta mejora a una exportación anterior, volvé a cargar y analizar
el documento original.
Quitar una variante o rechazar un grupo separa sus reemplazos. Editar la
etiqueta de un grupo confirmado cambia todas sus variantes.

En la vista previa podés comparar el texto original con el anonimizado y
seleccionar manualmente información que no haya sido detectada.

Para agregar un dato, elegí **Original**, seleccioná el texto, indicá su
categoría y pulsá **Solo anonimizar**. La selección que confirmás se respeta
exactamente, aunque sea una parte de una palabra o el análisis automático no
la reconozca. También se ocultan sus repeticiones iguales, sin distinguir
mayúsculas, cuando forman un dato completo.
Si la fila estaba desmarcada, se vuelve a activar al agregarla manualmente.
Usá **En grupo** únicamente cuando quieras asociar el dato a un grupo.
Comprobá el resultado en **Anonimizado** y luego en el archivo descargado.
Cambiar el tipo de una fila se conserva también al exportar.

La lupa permite buscar otras apariciones sin distinguir mayúsculas ni tildes.
Por defecto, `Ana` coincide en `Ana,` o `Ana.`, pero no dentro de `Mariana`
ni de `Ana@example.test`; `123` no coincide dentro de `123-456` o `+123`.
Los puntos, arrobas, barras, dos puntos, signos más, guiones y apóstrofos
entre letras o números mantienen unido el dato. Las letras, números, marcas
de acento y guiones bajos también forman parte de él.

Marcá **Permitir coincidencias parciales** para incluir fragmentos dentro de
palabras o datos compuestos. En la barra de selección, esta casilla solo
afecta las repeticiones: el fragmento que elegiste se conserva siempre.
En la lupa, modifica las coincidencias contadas, resaltadas y anonimizadas.
La opción vuelve a desactivarse al cargar otro documento; la selección
también vuelve al valor por defecto cada vez que elegís un fragmento nuevo.

Por ejemplo, en `121212`, si seleccionás los últimos cuatro dígitos, el
resultado por defecto es `12[DATO_1]`. Al permitir coincidencias parciales,
también se encuentra el primer `1212`: se cubre todo el número y el resultado
es `[DATO_1]`.

Si varias detecciones activas se superponen, se oculta toda la zona que
cubren, incluso si la superposición encadena varios fragmentos. La etiqueta
y el tipo aplicados corresponden a la última decisión manual sobre esas
filas, como agregar un dato, editar su etiqueta o confirmar un grupo.
Las demás apariciones de cada fila conservan su propia etiqueta y los grupos
no se unen por superponerse. Junto al campo editable se muestran las
sustituciones efectivamente aplicadas cuando difieren de la etiqueta de la
fila; una misma fila puede tener distintas sustituciones según la aparición.
Desactivar o eliminar la fila que prevalece deja decidir a las otras filas
activas y conserva la protección de los fragmentos que todavía cubren.

Si un grupo quedó con el tipo incorrecto, cambialo desde **Tipo de dato**
en ese mismo grupo. **Unir con otro grupo** permite elegir cualquier
destino. Cuando los tipos son distintos, se pide confirmar la reclasificación;
al aceptar, se conserva la categoría y el reemplazo del grupo de destino.
Las filas que habías desactivado permanecen desactivadas.

Cambiar el tipo de una fila o de un grupo conserva las etiquetas que
escribiste manualmente. Las etiquetas automáticas se ajustan al nuevo tipo.
Si editás la etiqueta de una variante de un grupo confirmado, se aplica a
todas sus variantes. Asignar una fila a otro grupo usa la etiqueta del
destino, porque estás eligiendo que pertenezca a esa identidad.

Al agregar, eliminar, cambiar el tipo o activar/desactivar una detección,
se actualizan las sugerencias de identidad. Se conservan los grupos que
confirmaste, creaste, editaste o separaste manualmente, además de los rechazos,
las etiquetas personalizadas y las filas desactivadas.

Si una nueva variante puede pertenecer a un grupo confirmado, aparece una
propuesta, por ejemplo **Incorporar a [PERSONA_1]**. Revisá el contexto y elegí
**Incorporar al grupo** para usar la etiqueta ya confirmada. La incorporación
no ocurre automáticamente. También podés rechazar la propuesta o elegir
otro destino mediante la unión manual.

### Paso 4 — Verificar y exportar

1. Hacé clic en **Abrir editor y verificar**.
2. Leé y corregí el texto anonimizado.
3. Ajustá fuente, tamaño, interlineado, márgenes o alineación.
4. Exportá a Word o PDF.

La fuente elegida se aplica a Word; el PDF usa Times Roman. Tamaño,
interlineado, alineación y márgenes se aplican a ambos formatos. La exportación
reconstruye el texto y no conserva el diseño original ni sus tablas.
Las ediciones del editor no cambian la tabla CSV ni se vuelven a analizar.

Un análisis completado habilita el editor y las descargas de Word y PDF
aunque no encuentre detecciones. También podés usarlos si después de una
revisión manual eliminaste la última fila o desactivaste todas. Un documento
recién cargado, todavía sin analizar ni revisar, no está listo para exportar.
Si el análisis falla o lo cancelás, se conserva el estado de la revisión
anterior.

Si cambiás las detecciones después de abrir el editor, volvé a **Abrir editor
y verificar** para regenerar el resultado. Las correcciones que hagas en el
editor se usan en la descarga; si borrás todo su contenido, se exporta un
documento vacío. La tabla CSV requiere detecciones y conserva los datos de
la tabla de revisión.

5. Descargá la tabla CSV de equivalencias si la necesitás.

> **Atención:** al editar manualmente, no restaures datos personales
> reales por error.

---

## 4. Consejos para mejores resultados

| Situación | Recomendación |
|-----------|---------------|
| Nombre no detectado | Agregalo manualmente desde la vista previa |
| Falso positivo | Desactivá la detección o usá “Ignorar similares” |
| Mismo dato repetido | Revisá la pestaña de grupos |
| Monto confundido con DNI | Revisá y desactivá esa detección |
| Documento largo | El análisis puede tardar unos segundos porque se ejecuta localmente |

---

## 5. Exportaciones

| Archivo | Contenido |
|---------|-----------|
| Word (.docx) | Documento anonimizado con el formato elegido |
| PDF | Documento anonimizado en formato PDF |
| CSV | Tabla de equivalencias entre original y etiqueta |
| Markdown | Texto anonimizado fácil de copiar en otra herramienta |

---

## 6. Privacidad y uso responsable

- Uso **personal y académico**.
- Procesamiento 100 % local.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.
- El CSV contiene las equivalencias con datos originales; no es un documento
  anonimizado para compartir indiscriminadamente.
- La detección automática **no es perfecta**.
- Revisá siempre el resultado antes de compartirlo.
- No publiques documentos reales, datos personales ni capturas sensibles
  en Issues o reportes de errores.

---

## 7. Cerrar la aplicación

Cerrar solo la pestaña del navegador puede no detener el programa que se
ejecuta por detrás.

### Windows

1. Cerrá la pestaña del navegador.
2. Abrí el Administrador de tareas (`Ctrl + Shift + Esc`).
3. Buscá `AnonimizadorJudicial-NLP.exe`.
4. Si hay varias copias, verificá su ruta para elegir la carpeta de la
   versión que querés cerrar.
5. Elegí **Finalizar tarea**.

Si el puerto está ocupado, `INICIAR.bat` busca otro puerto libre y conserva la copia anterior.
Guardá tus exportaciones antes de terminar esa copia y abrir otra.

### macOS

1. Cerrá la pestaña del navegador.
2. Abrí **Monitor de Actividad**.
3. Buscá `AnonimizadorJudicial-NLP`.
4. Elegí **Salir** o **Forzar salida**.

---

## 8. Glosario breve

| Término | Significado |
|---------|-------------|
| Detección | Dato personal identificado automáticamente |
| Placeholder o etiqueta | Texto de reemplazo, por ejemplo `[PERSONA_1]` |
| Cluster o grupo | Varias apariciones posiblemente pertenecientes al mismo dato |
| Presidio / spaCy | Motores de análisis de texto que corren localmente |

---

## 9. Checklist antes de compartir un documento

- [ ] Revisé todas las detecciones activas.
- [ ] Revisé los grupos sugeridos importantes.
- [ ] Leí el texto completo en el editor de verificación.
- [ ] Exporté el archivo correcto.
- [ ] Confirmé que no quedaron nombres, DNI, domicilios ni emails visibles.
- [ ] Revisé teléfonos, seguimiento, enlaces, expedientes, patentes, pólizas,
  números de chasis y motor.
