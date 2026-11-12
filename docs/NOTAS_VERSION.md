# Anonimizador Judicial 3.4.4

Edición IALAB del 12 de noviembre de 2026, basada en la versión funcional 3.4.4.
La copia original del MPF se conserva por separado.

## Disponibilidad

El código actualizado está en este repositorio. La publicación del portable
Windows IALAB está pendiente de construcción y verificación. Consultá el
[README](../README.md) para el estado actual y las instrucciones de inicio.

## Identidad IALAB

- Logo institucional, isotipo y favicon del paquete `marca-ialab-v2`.
- Paleta navy, violeta y azul acero del manual del laboratorio.
- Tipografía Roboto incluida localmente para conservar el funcionamiento sin conexión.
- Documentación y canal de distribución independientes en `anonimizador_uso_personal`.

## Novedades de 3.4.4

- Actualización de las dependencias compatibles y retirada de dos librerías
  que el programa no utiliza.
- Inventarios de dependencias generados desde el entorno de compilación y
  comprobación de la procedencia del ejecutable al preparar la descarga.
- Versión, enlaces de descarga, manuales y archivos del paquete alineados.
  Los informes de entregas anteriores se conservan en el archivo histórico
  del repositorio y no se incluyen en este portable.

## Funciones conservadas

- Las selecciones manuales respetan exactamente el texto marcado; las
  repeticiones usan límites completos salvo que actives coincidencias parciales.
- Los datos superpuestos se ocultan en toda su extensión y conservan la
  prioridad de la última decisión manual.
- Cambiar categorías conserva las etiquetas editadas; unir grupos usa la
  etiqueta del grupo de destino.
- Se permite verificar y exportar después del análisis aunque no queden
  detecciones. Las ediciones del texto, incluida una salida vacía, se respetan.
- El campo editable conserva el foco y la posición del cursor durante la revisión.

### Detección de nombres y carátulas

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

- Controles y flujo de revisión conservados, con la identidad visual IALAB
  aplicada a partir del manual suministrado.
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
- Procesamiento local y autoría IALAB del software; el modelo se incluye
  al construir el portable.

El detalle técnico está en [CHANGELOG.md](../CHANGELOG.md). Los resultados
de esta entrega se registran en [VERIFICACION_3.4.4.md](VERIFICACION_3.4.4.md).

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
