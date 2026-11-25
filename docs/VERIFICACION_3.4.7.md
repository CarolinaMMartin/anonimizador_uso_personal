# Verificación de la versión 3.4.7

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

Las regresiones cubren texto español con tildes combinadas, letras que requieren una fuente alternativa, conservación de decisiones manuales y confirmación al exportar un PDF con páginas sin texto. El PDF del incidente informado no estuvo disponible. Un mapa de caracteres incorrecto en el archivo de origen puede requerir una nueva copia con OCR.

La carpeta `Manuales` del ZIP contiene los tres PDF publicados con la 3.4.6, sin cambios: mencionan esa versión y su enlace de descarga apunta al ZIP anterior. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP. Los registros de ejecución están en [GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).

## Alerta de Defender en la 3.4.6

El 19 de noviembre de 2026, Microsoft Defender bloqueó la descarga del ZIP 3.4.6 con Chrome en un equipo con Windows 11. Las detecciones fueron `Trojan:Script/Wacatac.B!ml` y, con las definiciones actualizadas a 1.463.376.0, `Trojan:Script/Wacatac.C!ml`. Son clasificaciones heurísticas que señalan el ZIP completo. El detalle está en la [verificación de la 3.4.6](VERIFICACION_3.4.6.md).

En ese equipo se reprodujo el control de descargas y datos adjuntos de Defender con la protección activa y sin ejecutar el programa. El ZIP 3.4.6 publicado quedó bloqueado y el ZIP 3.4.5 pasó. También pasaron, por separado, el ejecutable, los tres PDF, la interfaz y el conjunto de archivos que cambiaron respecto de la 3.4.5. Un ZIP nuevo con los 969 archivos de la 3.4.6 pasó el mismo control. La detección quedó asociada al archivo ZIP publicado y no a un componente.

La 3.4.7 publica el mismo programa en un paquete nuevo. La alerta se atribuye a un falso positivo y no hay un dictamen de Microsoft. El paquete sigue sin firma digital y una detección heurística puede repetirse en esta u otra versión.

## Comprobación de este paquete

El [flujo de publicación](../.github/workflows/release-windows.yml) analiza el ZIP final con Defender antes de entregarlo. Ese examen no reproduce el control de descargas del navegador. Por eso el ZIP de esta versión se compila sin publicar, se somete al control de descargas en el equipo donde ocurrió el bloqueo y se publica ese mismo archivo solo si pasa. El resultado se registra en la [Release](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/tag/v3.4.7).

Si el antivirus bloquea la descarga, dejala bloqueada, evitá agregar exclusiones y [avisá en Issues](https://github.com/CarolinaMMartin/anonimizador_uso_personal/issues) con el nombre de la detección.
