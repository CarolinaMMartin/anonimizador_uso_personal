# Verificación de la versión 3.4.6

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

Las regresiones cubren texto español con tildes combinadas, letras que requieren una fuente alternativa, conservación de decisiones manuales y confirmación al exportar un PDF con páginas sin texto. El PDF del incidente informado no estuvo disponible. Un mapa de caracteres incorrecto en el archivo de origen puede requerir una nueva copia con OCR.

La carpeta `Manuales` del ZIP contiene los tres PDF de esta versión. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP. Los registros de ejecución están en [GitHub Actions](https://github.com/CarolinaMMartin/anonimizador_uso_personal/actions/workflows/release-windows.yml).
