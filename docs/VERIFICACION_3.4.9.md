# Verificación de la versión 3.4.9

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

## Cambios verificados

La corrección está en `frontend/app.js`; el servidor, la detección y las exportaciones no cambian respecto de la 3.4.8. Las regresiones nuevas están en [frontend_session.test.cjs](../tests/frontend_session.test.cjs) y cubren:

- que cada acción de revisión redibuje con su propia respuesta, sin volver a pedir el documento;
- que una copia idéntica del texto no haga depender del largo del documento cada consulta de posición;
- que la nota «Aplicado por aparición» coincida con el recorrido completo anterior, también con reemplazos solapados, contiguos y desactivados;
- que esa nota se calcule en menos de un segundo con 20.000 apariciones;
- que los desplegables de grupos compartan un único control de cierre, sin sumar uno en cada redibujado.

Los tiempos se midieron con la aplicación en Chrome 153 sobre Linux, con documentos ficticios y la detección reemplazada por una sintética de 230 filas y unos 100 grupos:

| Documento | Acción | 3.4.8 | 3.4.9 |
| --- | --- | --- | --- |
| 400.000 caracteres, 1.866 apariciones | Quitar una variante | 161 s | 0,4 s |
| 1.000.000 de caracteres, 4.637 apariciones | Quitar una variante | no medido | 0,85 s |
| 1.000.000 de caracteres, 4.637 apariciones | Desanonimizar un grupo de 3 variantes | no medido | 1,6 s |

Después de 40 acciones seguidas sobre el documento de 1.000.000 de caracteres, el tiempo por acción se mantuvo entre 0,7 y 0,85 s.

Una misma revisión de 18 pasos, ejecutada contra la 3.4.8 y contra esta versión, mostró la misma vista previa, tabla, grupos, contadores y avisos en cada paso. La suite de navegador (`tests/test_browser_manual_review.py`) se aprobó en Chromium 153; no se ejecutó en Edge.

El portable compilado desde el commit de la corrección se probó en Windows con un expediente largo y las acciones de revisión respondieron sin demoras. Esa compilación es anterior al cambio de número de versión.

## Límites conocidos

Desanonimizar un grupo, «Ignorar similares» y «Unir similares» siguen haciendo un pedido por variante, y el servidor recalcula las sugerencias en cada pedido. En documentos muy largos esas acciones pueden tardar algunos segundos.

## Contenido del paquete

La carpeta `Manuales` del ZIP contiene los tres PDF publicados con la 3.4.6, sin cambios: mencionan esa versión y no describen las novedades posteriores. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP.

## Comprobación antivirus

El flujo de publicación analiza el ZIP final con Defender, pero ese examen no reproduce el control de descargas del navegador que bloqueó la 3.4.6. Por eso el ZIP se compila sin publicar, se somete a ese control en Windows y se publica ese mismo archivo solo si pasa. El resultado se registra en la [Release](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/tag/v3.4.9). El paquete sigue sin firma digital y una detección heurística puede repetirse en esta u otra versión.

Si el antivirus bloquea la descarga, dejala bloqueada, evitá agregar exclusiones y [avisá en Issues](https://github.com/CarolinaMMartin/anonimizador_uso_personal/issues) con el nombre de la detección.
