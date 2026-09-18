# Verificación de 3.3.12

Revisión y validación local realizadas el 18 de septiembre de 2026 sobre Windows x64, Python 3.13.15, spaCy 3.8.14, modelo local 3.8.0 y Node.js 22.23.2.

- Revisión de los archivos publicables: código, frontend, catálogos, herramientas, documentación, avisos de terceros, plantillas y automatización. Se preservaron los cambios existentes en main antes de preparar la versión.
- Auditoría automática de sintaxis Python, JSON, compilación de regex, enlaces Markdown internos, archivos excluidos de publicación y consistencia de versión.
- `pip check`: sin incompatibilidades. El entorno completo se conserva en `dependencies-frozen.txt`.
- Pytest con el paquete construido: **247 pruebas y 765 subtests aprobados, sin omisiones**.
- Frontend: **18 pruebas de comportamiento aprobadas** mediante Node/VM. Estas pruebas simulan DOM y servidor; no equivalen a una prueba visual completa del navegador.
- Ejecutable: **46 comprobaciones** de agrupación, confirmación, separación, rechazo y exportación con sólo personas y todas las categorías.
- Ejecutable: **18 + 16 comprobaciones** de límites de entidades, firmas, catálogos y exportación en ambos modos.
- Inicio de Windows: **7 comprobaciones** de puerto ocupado, doble inicio, reutilización de proceso, conservación de sesión y verificación de la copia correcta.
- Word y cancelación: **14 comprobaciones** sobre el ejecutable. Los nombres de tablas, encabezados y pies se detectaron y ocultaron en vista previa, Word y PDF. La cancelación fue atendida durante el análisis.
- Compilación completa con PyInstaller: salida correcta. Se excluyeron los módulos de pruebas y benchmarks de spaCy/Thinc. Un aviso de recurso opcional `tzdata` no afectó las pruebas del programa; el producto no ofrece conversiones de zonas horarias.
- Distribución: política de archivos permitidos, exclusión de documentos/sesiones/registros/credenciales, carpeta interna versionada, validación de CRC y archivo SHA-256. Los recursos DOCX/PDF/CSV necesarios de dependencias se conservan únicamente si coinciden con los archivos de las distribuciones instaladas.

La segunda revisión y las pruebas de extracción del ZIP forman parte de la entrega local. La automatización de publicación vuelve a construir y probar el código antes de crear una Release.

## Límites verificados y pendientes

La detección es heurística: los tests no garantizan cobertura de todos los nombres ni ausencia de falsos positivos en cualquier documento. Las agrupaciones ambiguas requieren revisión.

No hay OCR. La extracción de Word cubre texto de párrafos, tablas, encabezados y pies; cuadros de texto, imágenes, notas y cambios pendientes requieren comprobación externa. Las exportaciones reconstruyen el texto. El PDF utiliza Times Roman. El CSV mantiene originales y etiquetas del análisis, no las ediciones libres del documento exportado.

Windows es la plataforma validada para esta entrega. macOS requiere construcción y pruebas propias. La función de personas conocidas permanece como propuesta para una versión posterior.

La suite emite dos avisos de deprecación de las dependencias del cliente de pruebas (Starlette/httpx y AnyIO); no son fallas de la aplicación. Se mantienen las dependencias fijadas del entorno validado.
