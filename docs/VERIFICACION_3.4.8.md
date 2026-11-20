# Verificación de la versión 3.4.8

El [flujo de publicación para Windows](../.github/workflows/release-windows.yml) construye el ejecutable desde el commit de la entrega. Ejecuta las regresiones de Python y JavaScript, abre el programa en Windows, analiza documentos ficticios, revisa las exportaciones y vuelve a abrir una copia extraída del ZIP antes de publicar.

## Cambios verificados

Las regresiones nuevas están en [test_person_lists_and_separators.py](../tests/test_person_lists_and_separators.py) y cubren:

- la apertura del navegador solo cuando el servidor acepta conexiones;
- enumeraciones de personas separadas por coma, con y sin «y» final, y la forma invertida «APELLIDO, Nombre», incluso con apellidos compuestos o en mayúsculas;
- frases formadas solo por términos abstractos, separadores «espacio-guion-espacio» y apellidos con guion;
- la lista de términos que nunca se anonimizan, sin distinguir mayúsculas, acentos ni espacios dobles, también cuando el término está pegado a un nombre.

La desanonimización desde grupos y desde la selección, el buscador de Detecciones y la separación del aviso de PDF se comprobaron en la aplicación con documentos ficticios. Las pruebas de interfaz existentes (`tests/frontend_session.test.cjs` y la suite de navegador) siguen aprobadas.

El documento original del informe de «Se rechazó la conexión» no estuvo disponible. La corrección elimina la causa reproducible: el navegador se abría antes de que el servidor escuchara.

## Contenido del paquete

La carpeta `Manuales` del ZIP contiene los tres PDF publicados con la 3.4.6, sin cambios: mencionan esa versión y no describen las novedades de la 3.4.8. El [manual de usuario](MANUAL_USUARIO.md) del repositorio sí las incluye. `SOURCE_COMMIT.txt` identifica el código usado y `BUILD_PROVENANCE.json` registra la huella del ejecutable. El archivo SHA-256 se publica junto al ZIP.

## Comprobación antivirus

El flujo de publicación analiza el ZIP final con Defender, pero ese examen no reproduce el control de descargas del navegador que bloqueó la 3.4.6. Por eso el ZIP se compila sin publicar, se somete a ese control en Windows y se publica ese mismo archivo solo si pasa. El resultado se registra en la [Release](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/tag/v3.4.8). El paquete sigue sin firma digital y una detección heurística puede repetirse en esta u otra versión.

Si el antivirus bloquea la descarga, dejala bloqueada, evitá agregar exclusiones y [avisá en Issues](https://github.com/CarolinaMMartin/anonimizador_uso_personal/issues) con el nombre de la detección.
