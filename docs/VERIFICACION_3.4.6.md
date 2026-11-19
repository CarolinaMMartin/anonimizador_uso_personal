# Verificación de la versión 3.4.6

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

Las regresiones cubren texto español con tildes combinadas, letras que requieren una fuente alternativa, conservación de decisiones manuales y confirmación al exportar un PDF con páginas sin texto. El PDF del incidente informado no estuvo disponible. Un mapa de caracteres incorrecto en el archivo de origen puede requerir una nueva copia con OCR.

La carpeta `Manuales` del ZIP contiene los tres PDF de esta versión. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP. Los registros de ejecución están en [GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).

## Alerta de Defender y comprobación posterior

El 19 de noviembre de 2026, Microsoft Defender bloqueó y quitó el ZIP 3.4.6 durante su descarga en un equipo con Windows 11. El registro de Defender identificó la detección `Trojan:Script/Wacatac.B!ml`, una clasificación heurística, con definiciones 1.463.330.0 del 16 de noviembre. El registro señala el ZIP completo y no identifica un archivo interno. El programa no llegó a ejecutarse.

En dos equipos desechables con Windows Server 2025 se comprobó el SHA-256 de los ZIP oficiales 3.4.5 y 3.4.6. Con Defender actualizado y protección en tiempo real activa se analizaron el ZIP, el ejecutable principal y la carpeta extraída. Las rutas de examen se comprobaron con `-CheckExclusion` en un volumen NTFS dedicado. Defender informó que no encontró amenazas. Chrome descargó ambos archivos desde el enlace público con su protección activa y el contenido coincidió con los SHA-256 publicados. [Registro de los dos exámenes y las descargas](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/runs/44610504729).

El mismo día, en el equipo donde ocurrió el bloqueo, se actualizaron las definiciones a la versión 1.463.376.0 con la protección en tiempo real activa. El ZIP 3.4.6 se descargó de nuevo sin alertas, su SHA-256 coincidió con el publicado (`582109b15827496403c098f0741c13ae163372b17ea8ab51b4a6e881d6f89f28`) y un examen explícito de Defender informó que no encontró amenazas. La comparación del código entre las etiquetas `v3.4.5` y `v3.4.6` y la revisión de los tres PDF agregados no mostraron contenido activo ni cambios en los lanzadores o en el flujo de publicación.

La alerta se atribuye a un falso positivo de las definiciones anteriores y la descarga 3.4.6 vuelve a ser la recomendada. No hay un dictamen de Microsoft sobre la muestra. El paquete sigue sin firma digital, por lo que una detección heurística puede repetirse en otros equipos.

### Si Defender bloquea la descarga

Actualizá las definiciones del antivirus desde Windows Update o desde Seguridad de Windows y volvé a descargar el ZIP. Mantené el antivirus activo y evitá agregar exclusiones o restaurar el archivo desde la cuarentena. Si el bloqueo continúa con las definiciones al día, dejá el archivo bloqueado y [avisá en Issues](https://github.com/CarolinaMMartin/anonimizador_uso_personal/issues) con el nombre de la detección.
