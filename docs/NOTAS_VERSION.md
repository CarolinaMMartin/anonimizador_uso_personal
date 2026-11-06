# Anonimizador Judicial 3.4.3

Entrega para Windows x64, con las correcciones de revisión del 6 de noviembre de 2026.

## Abrir la aplicación

[**DESCARGAR PARA WINDOWS — 3.4.3**](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/download/v3.4.3/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip)

El archivo es **AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip**:

1. Elegí **Extraer todo** y conservá la carpeta completa.
2. Abrí la carpeta extraída y ejecutá **INICIAR.bat**.
3. Esperá a que abra el navegador. Verificá **v3.4.3** y **Catálogos cargados**
   en la cabecera.

No requiere instalar Python ni descargar modelos. Para actualizar, guardá
el trabajo abierto y extraé esta entrega en una carpeta nueva. El sufijo
`revision-egm` distingue este paquete de la primera entrega local 3.4.3;
la aplicación muestra **v3.4.3** en ambos casos, por lo que debés usar el ZIP
enlazado arriba para recibir las correcciones de revisión.

## Correcciones incluidas en esta publicación

- Las selecciones manuales respetan exactamente el texto marcado; las
  repeticiones usan límites completos salvo que actives coincidencias parciales.
- Los datos superpuestos se ocultan en toda su extensión y conservan la
  prioridad de la última decisión manual.
- Cambiar categorías conserva las etiquetas editadas; unir grupos usa la
  etiqueta del grupo de destino.
- Se permite verificar y exportar después del análisis aunque no queden
  detecciones. Las ediciones del texto, incluida una salida vacía, se respetan.
- El campo editable conserva el foco y la posición del cursor durante la revisión.

## Cambios

- Las partes de una carátula se detectan completas también cuando están
  escritas en minúsculas y contienen nombres o apellidos fuera del catálogo.
  El procesamiento conserva esos límites para evitar dejar visible un apellido.
- Se contemplan carátulas con «c/» sin un asunto posterior y con «s/» sin una
  contraparte. Los separadores y el asunto permanecen fuera del nombre.
- Las empresas y los organismos de una carátula conservan su categoría.
  Los títulos de documentos y trámites no se toman como personas por estar
  seguidos de «s/».

Se mantienen las mejoras de las versiones anteriores:

- Los separadores de las carátulas judiciales delimitan las personas: el
  actor y el demandado no se convierten en un único nombre por aparecer
  unidos con «c/», y el asunto que sigue a «s/» queda fuera del nombre.
  Estos límites también se respetan al buscar repeticiones y variantes.
- Agregar, eliminar, reclasificar o activar/desactivar una detección
  actualiza las sugerencias de identidad. Se conservan los grupos confirmados
  o editados manualmente, las etiquetas, las exclusiones y los rechazos.
- Una variante compatible con un grupo confirmado se ofrece para revisión.
  Su incorporación requiere una decisión explícita y conserva la etiqueta
  de ese grupo.

- Estética, tipografías y controles coherentes con la entrega 3.4.1. El logo
  y la paleta siguen el manual MPFCABA Identidad 2026 V1 suministrado.
- Corrección del tipo de dato de un grupo y unión manual entre tipos, con
  confirmación y conservación del reemplazo de destino.
- Personas físicas bajo «Razón social», límites de campos de formulario e
  identificadores fiscales etiquetados.
- Saltos de línea y párrafos vacíos del editor respetados en Word y PDF.
- Detección unificada de documentos, teléfonos, patentes, expedientes,
  seguimiento de denuncias, pólizas, números de chasis y motor, y enlaces.
- Nombres y domicilios completos, incluidos apellidos compuestos, pisos,
  unidades, barrios, parcelas, entrecalles y variantes de escritura.
- Organismos y empresas con límites completos. Las repeticiones de
  identificadores y razones sociales se buscan dentro del mismo documento.
- Catálogos de personas utilizados directamente por el motor, con errores
  visibles si faltan o están dañados. Una falla no reemplaza la revisión anterior.
- Coincidencias superpuestas cubiertas íntegramente en resaltados y
  sustituciones. Los identificadores distintos no se agrupan por semejanza.
- Procesamiento local, modelo incluido y autoría IALAB del software.

El detalle técnico está en [CHANGELOG.md](../CHANGELOG.md). Los resultados
de la entrega inicial se registran en [VERIFICACION_3.4.3.md](VERIFICACION_3.4.3.md).
La verificación del paquete con las correcciones posteriores está en
[correcciones_pendientes.md](revision-egm/correcciones_pendientes.md).

## Uso y límites

Mantené **Otros** activada para incluir seguimiento de denuncias, pólizas,
chasis, motor y enlaces. Revisá el documento exportado antes de compartirlo.
La verificación utiliza documentos sintéticos; no demuestra cobertura de
cualquier documento posible.

Se necesita texto seleccionable: no se procesan escaneos ni imágenes mediante
OCR. Las exportaciones reconstruyen el texto y no conservan la distribución
original. El CSV de equivalencias contiene datos originales.

El ZIP es para Windows; no funciona en Mac ni en celulares. La entrega no
tiene firma digital. Consultá el [manual de instalación](MANUAL_INSTALACION.md)
si Windows impide ejecutarla.
