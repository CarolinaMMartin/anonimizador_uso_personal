# Licencias y privacidad — 3.3.13

Revisión técnica de la distribución: 18 de septiembre de 2026. Este documento describe los archivos incluidos y el funcionamiento; los términos aplicables están en las licencias originales.

## Código, marca y terceros

El código del proyecto se distribuye con [LICENSE](../LICENSE), Apache 2.0. [NOTICE](../NOTICE) contiene avisos de autoría y condiciones de uso de la marca institucional. La licencia del código no concede autorización para usar marcas.

[THIRD_PARTY_NOTICES.txt](../THIRD_PARTY_NOTICES.txt) enumera las dependencias principales fijadas en `requirements.txt`. El portable conserva textos de referencia en `LICENSES/` y copias de avisos originales de las distribuciones instaladas en `LICENSES/third_party/`.

`LICENSES/INVENTARIO_BUILD.json` identifica versiones y archivos de licencia del entorno de compilación. Puede incluir herramientas de desarrollo; no afirma que todas esas herramientas se ejecuten dentro del portable. Las versiones completas del entorno validado se documentan en [dependencies-frozen.txt](dependencies-frozen.txt).

## Modelo local

El paquete incluye `es_core_news_md` 3.8.0. Su licencia GPL-3.0 está en `models/es_core_news_md/LICENSE`, junto con su configuración y metadatos. Se conserva sin modificar. `LICENSES/GPL-3.0.txt` es una copia de referencia. La librería spaCy tiene licencia MIT; la licencia del modelo es independiente.

PyInstaller se utiliza para construir el ejecutable y tiene licencia GPL con excepción para su bootloader; conservar sus avisos originales incluidos en el inventario.

## Funcionamiento y datos

El servidor escucha en `127.0.0.1`. El análisis utiliza regex, Presidio y spaCy local. No hay OCR, LLM, servicios externos de IA ni telemetría.

Las sesiones y documentos cargados permanecen en memoria del proceso. El programa no crea automáticamente una base SQLite para guardar sesiones. Al cerrar la copia se pierde la sesión; las exportaciones guardadas por el usuario permanecen en disco. El almacenamiento SQLite auxiliar existe para desarrollo y no forma parte del flujo normal.

La entrega excluye sesiones, bases de datos, documentos de usuarios, equivalencias y registros. El CSV exportado contiene los valores originales: requiere el mismo cuidado que el documento de origen. Un texto anonimizado necesita revisión humana antes de compartirse.

La interfaz no utiliza CDN ni fuentes web. Presidio tiene desactivado su `EmailRecognizer`; los correos se detectan mediante regex. `app/detection/presidio_offline.py` configura tldextract con un snapshot local. [test_presidio_offline.py](../tests/test_presidio_offline.py) comprueba que esta capa no solicita recursos de red.

Descargar dependencias y el modelo durante la preparación del entorno requiere Internet; el portable validado funciona sin conexión.

Ver [DEPLOY.md](DEPLOY.md) y [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) para construcción y distribución.
