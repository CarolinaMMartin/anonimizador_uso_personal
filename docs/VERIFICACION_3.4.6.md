# Verificación de la versión 3.4.6

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

Las regresiones cubren texto español con tildes combinadas, letras que requieren una fuente alternativa, conservación de decisiones manuales y confirmación al exportar un PDF con páginas sin texto. El PDF del incidente informado no estuvo disponible. Un mapa de caracteres incorrecto en el archivo de origen puede requerir una nueva copia con OCR.

La carpeta `Manuales` del ZIP contiene los tres PDF de esta versión. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP. Los registros de ejecución están en [GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).

## Alerta de Defender y comprobación posterior

El 19 de noviembre de 2026, Microsoft Defender bloqueó y quitó una descarga del ZIP 3.4.6 durante su descarga en Windows. La distribución de esta versión quedó suspendida y la reemplaza la 3.4.7.

En dos equipos desechables con Windows Server 2025 se comprobó el SHA-256 de los ZIP oficiales 3.4.5 y 3.4.6. Con Defender actualizado y protección en tiempo real activa se analizaron el ZIP, el ejecutable principal y la carpeta extraída. Las rutas de examen se comprobaron con `-CheckExclusion` en un volumen NTFS dedicado. Defender informó que no encontró amenazas. Chrome descargó ambos archivos desde el enlace público con su protección activa y el contenido coincidió con los SHA-256 publicados. El resultado se limita a esos equipos y esas firmas. [Registro de los dos exámenes y las descargas](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/runs/44610504729).

El registro de Defender del equipo afectado, con Windows 11, identificó la detección `Trojan:Script/Wacatac.B!ml` en tres descargas con definiciones 1.463.330.0. Es una clasificación heurística que señala el ZIP completo y no identifica un archivo interno. Después de actualizar las definiciones a 1.463.376.0, una nueva descarga con Chrome volvió a quedar bloqueada, esta vez como `Trojan:Script/Wacatac.C!ml`, en el control de descargas y datos adjuntos. En ese mismo equipo, una copia obtenida sin navegador coincidió con el SHA-256 publicado y un examen explícito de Defender sobre el archivo en disco no encontró amenazas. Actualizar las definiciones no resuelve el bloqueo.

La comparación del código entre las etiquetas `v3.4.5` y `v3.4.6` y la revisión de los tres PDF agregados no mostraron contenido activo ni cambios en los lanzadores o en el flujo de publicación. No hay un dictamen de Microsoft.

En el equipo afectado se reprodujo después el control de descargas sin navegador. El ZIP 3.4.6 publicado quedó bloqueado, el ZIP 3.4.5 pasó y también pasó un ZIP nuevo con los mismos 969 archivos de la 3.4.6. Ningún componente probado por separado disparó la alerta. La detección quedó asociada al archivo ZIP publicado.

### Reemplazo

La 3.4.7 publica el mismo programa en un paquete nuevo. Usá la descarga del [README](../README.md) y consultá la [verificación de la 3.4.7](VERIFICACION_3.4.7.md). Si el antivirus quitó el ZIP 3.4.6, dejalo quitado.
