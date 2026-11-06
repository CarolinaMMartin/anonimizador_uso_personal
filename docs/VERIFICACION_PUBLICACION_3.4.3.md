# Verificación de la publicación 3.4.3

Revisión del 6 de noviembre de 2026 sobre el repositorio `CarolinaMMartin/anonimizador_mpf`, sus instrucciones de descarga y el ZIP Windows.

## Entrega vigente

- [Versión publicada](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/tag/v3.4.3).
- [ZIP Windows](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/download/v3.4.3/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip).
- [SHA-256](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/download/v3.4.3/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip.sha256).
- Tamaño del ZIP con documentación corregida: **145.422.123 bytes**.
- SHA-256: `158ce015a22a037b97adeccbc5213bff65da8bae2b8408977fbd76a3e3de0c5f`.
- Versión de la aplicación: **3.4.3**. Código del ejecutable: `91dc4eb896e26a95539d8c744d14a627a8b938c3`.

## Correcciones de publicación

Se corrigieron las instrucciones actuales de desarrollo y uso, los enlaces al repositorio anterior, las referencias a descargas Mac inexistentes y los manuales incluidos en el ZIP. El historial de cambios, las verificaciones anteriores y las propuestas se conservan con su contexto histórico; no identifican la descarga vigente.

La publicación automática toma el nombre del adjunto del enlace Windows validado en el README. Comprueba que repositorio, versión, archivo y checksum coincidan con el código. Las notas de una nueva Release convierten los enlaces relativos a enlaces al commit publicado.

El empaquetado también adapta los enlaces del historial de cambios a los archivos que efectivamente se entregan.

## Integridad del ZIP

Se actualizaron **14 archivos de documentación**. Las **1.743 entradas restantes** conservan exactamente los mismos bytes, incluidos el ejecutable, frontend, modelos, diccionarios, lanzadores, licencias e inventario de dependencias. Se verificaron las **1.757 entradas**, su orden, sus nombres y el CRC.

La revisión de **27 archivos de texto propios de la aplicación** no encontró enlaces relativos rotos ni referencias al repositorio o al nombre de descarga obsoletos. Los documentos históricos incluidos identifican expresamente la entrega que verificaron.

Esta actualización documental cambia el SHA-256 del ZIP. El checksum adjunto corresponde al archivo actualizado; no cambia el número de versión del ejecutable.

## Pruebas

- Suite Python: **1.081 aprobadas**, **765 subpruebas aprobadas**, **12 omitidas**, sin fallos.
- Las omisiones corresponden a 11 pruebas de navegador que requieren activación explícita y una prueba de enlaces simbólicos no habilitados en este entorno. El ejecutable no se modificó; su verificación previa de navegador se conserva en el [cierre EGM](revision-egm/correcciones_pendientes.md).
- Frontend: **45 pruebas aprobadas**, sin omisiones ni fallos.
- Dependencias: `pip check` sin incompatibilidades.
- Auditoría de estructura, sintaxis, reglas, enlaces locales y metadatos de descarga: sin errores.
- Nuevas regresiones de publicación: repositorio incorrecto, tag anterior, nombre del ZIP incoherente, checksum incorrecto, enlaces relativos de notas y enlaces del historial dentro del portable.

Las evidencias de esta revisión están en `build/release-publication-audit/`, fuera del código publicado. No se usaron documentos reales.

## Límites vigentes

La entrega sigue sin firma digital y puede ser bloqueada por las políticas de Windows. No hay un paquete macOS de esta versión. Las pruebas no garantizan ausencia de todo defecto: acreditan los controles descritos y la integridad de esta entrega.
