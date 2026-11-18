# Verificación de 3.4.5 · Actualización de estética IALAB

Entrega del 18 de noviembre de 2026. Incluye el encabezado blanco, el logo
azul, los paneles redondeados y los botones actualizados. Conserva la lógica
de anonimización de 3.4.4; cambia la versión del programa y de su descarga.

## Comprobaciones de publicación

La publicación se realiza mediante el workflow
[Build and verify portable (Windows)](../.github/workflows/release-windows.yml).
El job de publicación depende del éxito de la construcción y verificación:

- Auditoría de archivos, enlaces de descarga y versiones; comprobación de dependencias.
- Pruebas Python y Node antes de construir; repetición de Python con el portable.
- Construcción desde el mismo commit indicado en SOURCE_COMMIT.txt.
- Inicio real de Windows, doble apertura y conservación de instancias previas.
- Análisis por categorías, grupos, partes de documentos y datos sensibles.
- Identidades, carátulas y exportaciones con documentos ficticios.
- Procedencia del ejecutable, integridad CRC del ZIP y checksum SHA-256.
- Extracción del ZIP en una carpeta nueva, inicio y análisis/exportación de esa copia.

Los resultados efectivos y registros de cada ejecución se consultan en
[GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).
Una ejecución fallida no publica la Release. El paquete es
`AnonimizadorJudicial-3.4.5-Windows.zip`, con un checksum del mismo nombre
terminado en `.sha256`; ambos están enlazados en el [README](../README.md).

## Alcance y límites

La revisión estática del cambio visual conservó los 67 IDs del HTML y la
referencia a la lógica JavaScript. La revisión visual interactiva quedó
pendiente por una limitación de identificación de URL de la herramienta de
navegador; las pruebas funcionales no sustituyen esa revisión visual.

El inventario de dependencias de esta entrega se genera dentro del paquete;
`docs/dependencies-frozen.txt` conserva la referencia del build 3.4.4.
Las verificaciones de 3.4.4 no se presentan como resultados del nuevo binario.

El portable no está firmado digitalmente. No incluye OCR ni versión para
macOS. Las pruebas usan documentos ficticios y no garantizan detección de
todos los datos personales; la revisión humana sigue siendo necesaria.
