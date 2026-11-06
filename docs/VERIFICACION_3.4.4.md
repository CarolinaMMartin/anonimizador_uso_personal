# Verificación de 3.4.4

Entrega construida y validada el **6 de noviembre de 2026**, con documentos
ficticios y pruebas sobre el ejecutable Windows. La aplicación, la interfaz,
los manuales y la descarga identifican la versión **3.4.4**.

## Alcance de la entrega

- Aplicación: Anonimizador Judicial 3.4.4 para Windows x64.
- Paquete: `AnonimizadorJudicial-3.4.4-Windows.zip`.
- Carpeta local: `dist/AnonimizadorJudicial-NLP-3.4.4/`.
- Carpeta interna del ZIP: `AnonimizadorJudicial-NLP-3.4.4/`.
- Entorno usado: Python 3.12.14 de 64 bits, en un entorno virtual aislado.

La actualización retira las dependencias sin uso `aiofiles` y
`presidio-anonymizer`, actualiza las dependencias compatibles y genera los
inventarios desde el entorno de compilación. El empaquetado comprueba la
procedencia del ejecutable y conserva los inventarios y licencias del build.

Los informes de versiones anteriores se conservan en
[el archivo histórico](historico/README.md); no validan esta entrega.

## Resultados observados

| Comprobación | Resultado |
| --- | --- |
| Suite Python con el portable y navegador real | **1.108 aprobadas**, **765 subpruebas aprobadas**, sin fallos |
| Pruebas de navegador incluidas en esa suite | **11 aprobadas**, con Edge, selección real y descargas Word/PDF |
| Pruebas de la interfaz JavaScript | **45 aprobadas** |
| Dependencias | `pip check` sin incompatibilidades; **86 distribuciones** en el entorno aislado |
| Auditoría del repositorio | **192 archivos y 73 enlaces locales**, sin errores |
| Procedencia de compilación | **88 archivos fuente y 716 archivos de ejecución** registrados y comprobados |
| Arranque Windows | Doble apertura, reutilización de instancia, puerto y versión correctos |
| Anonimización y exportación | Categorías, nombres, agrupación, partes de documentos, identidad y carátulas aprobadas |

La única omisión es una prueba de enlaces simbólicos que este Windows no
permite crear. La suite emite una advertencia de deprecación del cliente de
pruebas de Starlette; no hubo errores de ejecución ni fallos de pruebas.

Se comprobó que `aiofiles` y `presidio_anonymizer` no están instalados ni
incluidos como módulos en el ejecutable. El entorno no hereda paquetes
globales. Los inventarios de texto y JSON proceden de una misma captura;
[dependencies-frozen.txt](dependencies-frozen.txt) reproduce el inventario
del paquete validado.

Las versiones transitivas respetan las restricciones del motor NLP: NumPy
2.4.6, preshed 3.0.13 y Thinc 8.3.14. El modelo español 3.8.0 es compatible
con spaCy 3.8.18; se verifica su versión y su correspondencia con el modelo
instalado. No se reemplazan por versiones mayores incompatibles.

## Archivos e integridad de la entrega

La entrega incluye únicamente los manuales y el informe de verificación de
3.4.4. Los antecedentes se conservan en `docs/historico/`; los paquetes
locales anteriores están archivados en `_archivo/`, fuera de Git y de la
descarga vigente. El empaquetado excluye sesiones, documentos de usuarios,
equivalencias, registros, credenciales y archivos de control temporales.

`BUILD_PROVENANCE.json` registra las dependencias y las huellas del código,
el ejecutable, las bibliotecas, los modelos, la interfaz y los lanzadores.
El empaquetador verifica esa procedencia antes de actualizar documentación;
no vuelve a generar inventarios con un entorno distinto del utilizado para
compilar.

El commit de los fuentes se consigna en `SOURCE_COMMIT.txt` dentro del ZIP
y en la etiqueta `v3.4.4`. El tamaño exacto y la huella SHA-256 del archivo
final se publican en la [Release 3.4.4](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/tag/v3.4.4)
y en su [archivo SHA-256](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/download/v3.4.4/AnonimizadorJudicial-3.4.4-Windows.zip.sha256).
Antes de dar por cerrada la publicación se descarga ese adjunto, se compara
con el ZIP local y se comprueba su CRC, arranque, capas NLP y exportaciones.

Las evidencias y registros de esta entrega se conservan localmente en
`build/release-3.4.4/`, fuera del código publicado.

## Límites

La entrega es para Windows y todavía no tiene firma digital. No hay un
paquete macOS de esta versión. El procesamiento requiere DOCX o PDF con
texto seleccionable; no incluye OCR. Las comprobaciones deben emplear
documentos ficticios y no sustituyen la revisión humana del resultado.
