# Verificación de 3.4.1

Entrega local para Windows x64, 5 de noviembre de 2026. Se utilizan
documentos sintéticos; los archivos privados aportados para diagnosticar
el problema no se incorporan al código ni al paquete.

## Alcance

La interfaz recupera Segoe UI, la fuente documental Georgia/Times y las
proporciones anteriores. La paleta y la composición del logo se contrastan
con «MPFCABA Identidad 2026 V1», páginas 4, 5 y 12–19. La preferencia explícita
de conservar las tipografías anteriores se aplica a la interfaz del producto.

Se verifica la clasificación de formularios y la corrección manual de grupos,
incluida la unión entre categorías con reclasificación explícita.
La exportación respeta los saltos de línea y párrafos del texto revisado,
incluidos párrafos vacíos; la limpieza de líneas PDF queda en la extracción.

## Resultados

- Suite Python sobre la entrega compilada: 731 pruebas y 765 subpruebas
  aprobadas. Una prueba de enlaces simbólicos se omite porque requiere
  privilegios de Windows. Se registra una advertencia de Starlette.
- Interfaz: 29 pruebas de Node aprobadas.
- Auditoría del repositorio: 164 archivos, 112 módulos Python, 4 JSON y
  36 enlaces internos revisados; sin errores.
- Ejecutable: siete comprobaciones del lanzador aprobadas, sin cerrar la
  instalación anterior. Motor NLP y catálogos disponibles localmente.
- Pruebas integradas de categorías, agrupación, correcciones manuales,
  partes de Word y cancelación aprobadas. Los ejemplos de datos sensibles
  se verifican también en el texto exportado a Word y PDF.
- Playwright con Chrome en un perfil de pruebas separado: 16 comprobaciones
  aprobadas, sin errores de JavaScript. Se prueba carga, análisis, cambio
  de categoría del grupo, tipografía, alineación y descarga de ambos formatos.
  El botón de detener aparece solamente durante el procesamiento. En las
  descargas reales se comprueban también los saltos de línea y la sustitución
  consistente de nombres repetidos. Se inspecciona la página PDF renderizada.
- Inspección de capturas en escritorio (1440 × 1000) y móvil (390 × 844):
  inicio, detecciones, grupos y editor. No se observa desbordamiento de la
  página; la tabla mantiene desplazamiento horizontal propio en móvil.
  Se compara el inicio con la interfaz anterior obtenida del código base,
  en el mismo tamaño de pantalla.

Las evidencias locales se conservan en `build/validation/ui341`. El resultado
de integridad y arranque del ZIP final se registra junto a la entrega en
`dist/VERIFICACION_ENTREGA_3.4.1.txt`.

## Límites

La detección requiere revisar el resultado. No hay OCR. Las exportaciones
reconstruyen el texto y no conservan la distribución original. El CSV
contiene equivalencias con valores originales. El ejecutable no está firmado.

Las sesiones permanecen en memoria y no migran automáticamente entre
versiones. La instalación anterior se conserva para no interrumpir una
revisión abierta. No se publica una versión en GitHub como parte de esta entrega.
