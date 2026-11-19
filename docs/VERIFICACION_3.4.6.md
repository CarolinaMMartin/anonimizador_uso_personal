# Verificación de la versión 3.4.6

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

Las regresiones cubren texto español con tildes combinadas, letras que requieren una fuente alternativa, conservación de decisiones manuales y confirmación al exportar un PDF con páginas sin texto. El PDF del incidente informado no estuvo disponible. Un mapa de caracteres incorrecto en el archivo de origen puede requerir una nueva copia con OCR.

La carpeta `Manuales` del ZIP contiene los tres PDF de esta versión. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP. Los registros de ejecución están en [GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).

## Alerta de Defender y comprobación posterior

El 19 de noviembre de 2026, Microsoft Defender bloqueó y quitó una descarga del ZIP 3.4.6 durante su descarga en Windows. La distribución de esta versión sigue en revisión.

En dos equipos desechables con Windows Server 2025 se comprobó el SHA-256 de los ZIP oficiales 3.4.5 y 3.4.6. Con Defender actualizado y protección en tiempo real activa se analizaron el ZIP, el ejecutable principal y la carpeta extraída. Las rutas de examen se comprobaron con `-CheckExclusion` en un volumen NTFS dedicado. Defender informó que no encontró amenazas. Chrome descargó ambos archivos desde el enlace público con su protección activa y el contenido coincidió con los SHA-256 publicados. El resultado se limita a esos equipos y esas firmas. No se determinó qué disparó la alerta original. [Registro de los dos exámenes y las descargas](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/runs/44610504729).

### Alternativa temporal para Windows

Para continuar con la edición anterior, [descargá el ZIP oficial 3.4.5](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/download/v3.4.5/AnonimizadorJudicial-3.4.5-Windows.zip) y extraelo en una carpeta nueva. Usá documentos Word o PDF con texto digital en todas las páginas. En 3.4.5, volver a analizar después de corregir puede descartar la revisión manual. Revisá en la exportación los reemplazos, los acentos y que esté presente todo el texto antes de compartirla. Si el antivirus bloquea la descarga, dejala bloqueada.
