# Cambios — Anonimizador Judicial

## 3.4.4 — 6 de noviembre de 2026

La [descarga vigente](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/tag/v3.4.4)
usa un único paquete Windows identificado como 3.4.4.

- Actualiza las dependencias compatibles y retira `aiofiles` y
  `presidio-anonymizer`, que el código no utiliza.
- Genera los inventarios de dependencias desde el entorno de compilación.
  Comprueba la procedencia del ejecutable antes de volver a empaquetarlo,
  para evitar mezclar archivos o inventarios de distintos builds.
- Alinea la versión de la aplicación, la interfaz, los manuales, los enlaces
  de descarga y el paquete. Conserva las correcciones funcionales de 3.4.3.
- Separa los informes de entregas anteriores en `docs/historico/`; esos
  informes no forman parte del portable vigente.
- El entorno de desarrollo requiere Python 3.12–3.13.

Las comprobaciones de esta entrega se registran en
[VERIFICACION_3.4.4.md](docs/VERIFICACION_3.4.4.md).

## 3.4.3 — 6 de noviembre de 2026

La entrega 3.4.3 incorporó las correcciones de la revisión EGM:

- Respeta exactamente la selección manual, incluso dentro de una palabra.
  Sus repeticiones y la lupa usan límites completos por defecto; el usuario
  puede activar coincidencias parciales.
- Oculta toda la extensión de datos superpuestos y aplica la etiqueta de
  la última decisión manual; las otras apariciones conservan sus etiquetas.
- Preserva etiquetas manuales al cambiar categorías y aplica la etiqueta
  del destino al asignar o unir grupos.
- Habilita el editor y las exportaciones tras el análisis aunque no queden
  detecciones, y respeta las ediciones del texto, incluida una salida vacía.
- Mantiene el foco y el cursor al editar etiquetas, y actualiza las variantes
  del grupo y la vista anonimizada después del guardado.
- Corrige coincidencias y posiciones con tildes descompuestas y emojis.

También incluye las mejoras iniciales de 3.4.3:

- Conserva nombres completos en minúsculas y fuera del catálogo cuando
  ocupan una parte delimitada de carátula. Los separadores `c/` y `s/`
  permanecen fuera de las entidades.
- Comparte los límites de las partes entre extracción, limpieza y validación,
  incluidas carátulas sin materia y presentaciones con `s/` sin demandado.
- Verifica carátulas con errores de escritura, orden invertido, distintas
  mayúsculas y saltos de línea, preservando el asunto y la prosa ordinaria.
- Conserva la categoría de empresas y organismos que sean partes, y excluye
  títulos de documentos y trámites de las detecciones de personas.

## 3.4.2 — 6 de noviembre de 2026

- Respeta los separadores de partes y materia de las carátulas antes de
  aceptar detecciones por contexto. Las coincidencias de NLP que atraviesan
  esos límites no unen al actor con el demandado.
- Distingue enumeraciones de personas de apellidos unidos por «y», incluidos
  fragmentos de nombres producidos por los saltos de línea de un PDF.
- Actualiza las sugerencias después de corregir detecciones, conservando
  confirmaciones, rechazos, separaciones y reemplazos manuales. La incorporación
  de una variante a un grupo confirmado requiere una acción explícita.
- Verifica identidades completas desde la carga de Word/PDF hasta la vista
  previa y las exportaciones Word, PDF y CSV, con casos ficticios de nombres
  completos, apellidos compuestos, abreviaciones y variantes de orden.

## 3.4.1 — 5 de noviembre de 2026

- Recupera la tipografía, proporciones, superficies y jerarquía de acciones
  de la interfaz anterior, con la paleta del manual MPFCABA Identidad 2026 V1.
- Permite corregir el tipo desde el grupo y unir manualmente entidades de
  categorías distintas mediante una reclasificación explícita, conservando
  las posiciones, la revisión y el reemplazo del grupo de destino.
- Delimita los campos de formularios antes de clasificarlos: una persona
  bajo «Razón social» sigue siendo persona y no absorbe el campo siguiente.
- Corrige organismos bajo etiquetas fiscales, códigos administrativos
  confundidos con patentes y valores de CUIT vacíos o ficticios.
- Incluye identificadores fiscales etiquetados, como CAE/CAI, números de
  comprobantes e ingresos brutos, entre los datos sensibles.
- Conserva los saltos de línea y párrafos del editor al exportar a Word
  y PDF, sin volver a aplicar la limpieza de líneas de la extracción PDF.
- Permite construir una copia en otra carpeta de entrega para conservar
  intactas las versiones abiertas.

## 3.4.0 — 5 de noviembre de 2026

- Detección y validación compartidas para documentos, teléfonos, patentes,
  expedientes, seguimiento de denuncias, pólizas, chasis, motor y enlaces.
  Los códigos sin categoría propia se muestran como «Otros» (`DATO`).
- Domicilios con componentes completos: vías sin prefijo, pisos, unidades,
  ordinales, barrios, parcelas y entrecalles. Organismos y empresas conservan
  sus nombres completos y límites frente a la prosa.
- Nombres detectados desde los catálogos cargados, incluidos compuestos,
  partículas, iniciales y variantes de escritura. Los catálogos externos
  complementan los incluidos; un recurso ausente o inválido detiene el análisis
  y conserva la revisión anterior.
- Repeticiones documentales de identificadores y razones sociales sin su
  etiqueta o sufijo. Las coincidencias superpuestas conservan toda su cobertura.
- Los identificadores distintos dejan de agruparse por semejanza de caracteres;
  las variantes de formato de DNI, CUIT, teléfono y patente comparten sustitución.
- Identidad visual MPF en la interfaz: logo íntegro, paleta institucional y
  tipografía del sistema; controles, estados y resaltados consistentes.
- Regresiones de detección, categorías, catálogos, revisión y exportación a
  Word/PDF con datos sintéticos. La entrega local incluye el motor NLP y sus
  recursos. La descarga publicada en GitHub no se modifica automáticamente.


## 3.3.13 — Correcciones manuales y descarga accesible

- La selección manual respeta la categoría elegida, incluidos domicilios como
  «Campana 39» y otros datos que no reconoce el análisis automático.
- Volver a agregar un dato existente lo activa y conserva su sustitución.
- La vista final, Word, PDF y CSV respetan las filas revisadas sin volver a
  descartarlas mediante filtros automáticos.
- Se corrigen las posiciones entre navegador y servidor en textos con emojis
  u otros caracteres fuera del plano Unicode básico.
- La búsqueda usa el texto actual aunque se pulse antes de terminar la espera
  de actualización. Una selección pendiente no se aplica a otro documento.
- README orientado a personas sin conocimientos técnicos, con descarga directa
  de Windows, inicio paso a paso y ayuda para el agregado manual.
- Regresiones automatizadas de selección, categorías, reactivación, grupos,
  posiciones Unicode y exportaciones con datos ficticios.

## 3.3.12 — 18 de septiembre de 2026

- Detección de nombres y apellidos con cualquier capitalización y tildes, basada en los catálogos locales y contexto de personas. Los límites evitan absorber oraciones completas.
- Empresas y organismos con límites propios; protección de vehículos, códigos y otras entidades frente a detecciones de personas.
- Agrupación de variantes en el documento completo: orden invertido, iniciales, nombres parciales y apellidos compuestos. Las coincidencias ambiguas permanecen separadas.
- Detección de apellidos ausentes del catálogo mediante nombres completos encontrados en el documento, conservando evidencia y procedencia.
- Identificadores y etiquetas estables; confirmación, separación y rechazo de agrupaciones coherentes con la exportación.
- Correcciones de guardado, cambio de sesión y exportación en la interfaz.
- NLP sobre todo el texto mediante fragmentos superpuestos: se elimina el corte silencioso a 500.000 caracteres.
- Cancelación atendida durante el análisis; ejecución del análisis en el pool de trabajo.
- Extracción de párrafos, tablas, tablas anidadas, encabezados y pies de Word.
- Carga limitada a 40 MB y rechazo explícito de formatos no admitidos.
- Protección del CSV frente a fórmulas precedidas por espacios.
- Inicio de Windows con puerto disponible y reutilización de la misma copia, conservando otros procesos.
- Manuales y avisos de terceros actualizados; ZIP versionado con SHA-256, exclusión de datos de usuarios e inventario de licencias.

La entrega de esta versión corresponde a Windows x64. macOS requiere su propia compilación y validación. La función de personas conocidas queda pendiente para otra versión.

## Versiones anteriores

Las entradas anteriores conservan el historial del proyecto; no son enlaces
a la descarga vigente. Las revisiones locales intermedias de 3.3.11 se
consolidaron en 3.3.12. Para instalar la aplicación, usá la descarga indicada
en el [README](README.md).
