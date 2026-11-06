# Construcción y distribución — 3.4.3

La entrega 3.4.3 corresponde a Windows x64. Todavía no hay una entrega Mac de esta versión en `anonimizador_mpf`; debe compilarse y validarse en una Mac antes de publicarse.

La [Release 3.4.3](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/tag/v3.4.3)
distribuye el paquete con las correcciones de la revisión EGM:
`AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip` y su SHA-256.
La carpeta local verificada es `dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm/`.
La primera entrega local con el mismo número no incluye esas
correcciones y no es el archivo de esta publicación. Generar un ZIP local
no publica una Release ni modifica las descargas existentes.

## Bloqueo de Windows 11 pendiente de resolver

La compilación 3.4.3 no está firmada. El Control Inteligente de Aplicaciones
puede bloquear el ejecutable o el lanzador en algunos equipos. Una prueba
funcional en Windows sin esa protección no demuestra que el paquete se pueda
abrir en Windows 11 con la protección activa.

Para una entrega accesible hay que identificar el archivo concreto bloqueado
en el registro de integridad de código de Windows; obtener una identidad de
firma válida; reemplazar el inicio mediante BAT/PowerShell por un lanzador
firmado si estos archivos también se bloquean; firmar los binarios distribuidos
antes de empaquetar; y probar el ZIP extraído en un Windows 11 con Control
Inteligente de Aplicaciones activado. Firmar solo el ZIP no firma los archivos
que se ejecutan dentro. Hasta entonces, informar el bloqueo en el README y
no presentar el ZIP como compatible con todos los equipos Windows 11.

## Construcción

Desde la raíz del repositorio, con Python 3.11–3.13:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
$env:ANON_PKG_DIR = 'dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm'
.venv\Scripts\python -m pytest tests -q
node --test tests/frontend_session.test.cjs
.venv\Scripts\python scripts\audit_repository.py
.venv\Scripts\python scripts\build_portable_full.py --output dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python scripts\check_windows_launcher.py --package dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm --keep-running
$appPort = Get-Content -LiteralPath 'dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm/PUERTO_ACTUAL.txt'
.venv\Scripts\python scripts\portable_smoke.py --package dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm --port $appPort --use-existing --category-cases --all-categories
.venv\Scripts\python scripts\check_sensitive_portable.py --package dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm --port $appPort
.venv\Scripts\python scripts\check_identity_flow.py --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\check_identity_flow.py --caption-cases --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\package_release.py --package dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm --output dist/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip
```

La instalación descarga dependencias y el modelo fijo `es_core_news_md` 3.8.0. Un modelo local válido evita volver a descargarlo. El programa empaquetado funciona sin conexión.

`build/` contiene archivos temporales de compilación y `dist/` el resultado generado; no son versiones independientes del código. La versión se obtiene de `APP_VERSION` en [config.py](../app/config.py) y figura en `VERSION_APP.txt`, la interfaz y `/health`.

El constructor produce un paquete completo: ejecutable, frontend, diccionarios internos, modelo, lanzadores, manuales y licencias. El empaquetador rechaza un ejecutable con otra versión y genera un ZIP con carpeta interna versionada y un archivo SHA-256.

`--output` acepta únicamente una carpeta nueva dentro de `dist/`. Permite
construir la actualización sin reemplazar una instalación abierta. Sin esa
opción se conserva la salida tradicional `dist/AnonimizadorJudicial-NLP/`.
Si una ruta de compilación resulta demasiado larga en Windows, se puede
elegir un staging corto mediante `ANON_BUILD_DIR`, por ejemplo `build/p343`.

## Verificación de la entrega

Probar el ZIP extraído en una carpeta nueva. Ejecutar `INICIAR.bat`; el lanzador muestra la dirección y busca un puerto libre entre 8787 y 8796. No cierra otras copias. En `/health`, verificar `app_version`, `nlp_layers.presidio.available` y `nlp_layers.spacy.available`. Verificar también carga, análisis, agrupación y exportaciones con documentos ficticios.

Las pruebas de estructura del paquete se omiten antes de construirlo; después de construirlo deben ejecutarse sin omisiones. Para verificar otra carpeta, establecer `ANON_PKG_DIR`.

No distribuir documentos reales, equivalencias de usuarios, sesiones, bases de datos, registros, credenciales ni archivos de configuración personales. Los resultados de validación permanecen en `build/validation/`, fuera de Git y de la entrega.

## Publicación y actualización

Publicar el código en Git y el ZIP como adjunto de una Release; nunca incorporar ejecutables o modelos al historial. Conservar `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.txt`, `LICENSES/` y la licencia del modelo. Revisar las condiciones de marca en [NOTICE](../NOTICE) antes de reutilizar el logo.

Para actualizar, extraer la nueva versión en otra carpeta y guardar las exportaciones antes de cerrar una sesión anterior. Las sesiones se mantienen en memoria y no migran entre procesos.

Ver [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), [COMPLIANCE.md](COMPLIANCE.md) y [MANUAL_INSTALACION.md](MANUAL_INSTALACION.md).
