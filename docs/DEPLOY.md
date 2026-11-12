# Construcción y distribución — 3.4.4

Esta edición IALAB se publica en `CarolinaMMartin/anonimizador_uso_personal`.
El portable Windows 3.4.4 se distribuye como
`AnonimizadorJudicial-3.4.4-Windows.zip`,
acompañado por su SHA-256. La carpeta local de compilación es
`dist/AnonimizadorJudicial-NLP-3.4.4/`.

Generar un ZIP local no publica una Release ni modifica las descargas
existentes. Los resultados de esta copia se registran en
[VERIFICACION_3.4.4.md](VERIFICACION_3.4.4.md). Los resultados históricos del
MPF no validan el nuevo paquete. macOS requiere construir y verificar un
paquete propio en ese sistema.

## Bloqueo de Windows 11 pendiente de resolver

La compilación 3.4.4 no está firmada. El Control Inteligente de Aplicaciones
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

Desde la raíz del repositorio, con Python 3.12–3.13:

Usar un entorno virtual aislado, sin `--system-site-packages`; no reutilizar
dependencias heredadas de otra instalación de Python.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
$env:ANON_PKG_DIR = 'dist/AnonimizadorJudicial-NLP-3.4.4'
.venv\Scripts\python -m pytest tests -q
node --test tests/frontend_session.test.cjs
.venv\Scripts\python scripts\audit_repository.py
.venv\Scripts\python scripts\build_portable_full.py --output dist/AnonimizadorJudicial-NLP-3.4.4
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python scripts\check_windows_launcher.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --keep-running
$appPort = Get-Content -LiteralPath 'dist/AnonimizadorJudicial-NLP-3.4.4/PUERTO_ACTUAL.txt'
.venv\Scripts\python scripts\portable_smoke.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --port $appPort --use-existing --category-cases --all-categories
.venv\Scripts\python scripts\check_sensitive_portable.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --port $appPort
.venv\Scripts\python scripts\check_identity_flow.py --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\check_identity_flow.py --caption-cases --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\package_release.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --output dist/AnonimizadorJudicial-3.4.4-Windows.zip
```

La instalación descarga dependencias y el modelo fijo `es_core_news_md` 3.8.0. Un modelo local válido evita volver a descargarlo. El programa empaquetado funciona sin conexión.

`build/` contiene archivos temporales de compilación y `dist/` el resultado generado; no son versiones independientes del código. La versión se obtiene de `APP_VERSION` en [config.py](../app/config.py) y figura en `VERSION_APP.txt`, la interfaz y `/health`.

El constructor produce un paquete completo: ejecutable, frontend, diccionarios internos, modelo, lanzadores, manuales y licencias. El empaquetador rechaza un ejecutable con otra versión y genera un ZIP con carpeta interna versionada y un archivo SHA-256.

`--output` acepta únicamente una carpeta nueva dentro de `dist/`. Permite
construir la actualización sin reemplazar una instalación abierta. Sin esa
opción se conserva la salida tradicional `dist/AnonimizadorJudicial-NLP/`.
Si una ruta de compilación resulta demasiado larga en Windows, se puede
elegir un staging corto mediante `ANON_BUILD_DIR`, por ejemplo `build/p344`.

## Procedencia e inventarios

El constructor registra el entorno instalado antes de compilar y comprueba
que se conserve durante la construcción. Genera juntos
`DEPENDENCIAS_BUILD.txt` y `LICENSES/INVENTARIO_BUILD.json`; ambos describen
ese entorno e incluyen las herramientas de desarrollo utilizadas.

`BUILD_PROVENANCE.json` registra Python, plataforma, distribuciones,
procedencia de instalaciones directas, huellas SHA-256 de los fuentes que
intervienen en la compilación y huella del ejecutable. Al volver a empaquetar,
se exige que coincidan el entorno, esos fuentes y el binario. Una diferencia
detiene el proceso antes de actualizar documentación o licencias: construir
una nueva entrega si cambió alguno de esos componentes.

El empaquetado conserva los inventarios y avisos de terceros generados por
el build. Para actualizar la referencia del repositorio, copiar
`DEPENDENCIAS_BUILD.txt` del paquete final a `docs/dependencies-frozen.txt`.
Ese archivo del repositorio no se usa para crear el inventario del portable.

## Verificación de la entrega

Probar el ZIP extraído en una carpeta nueva. Ejecutar `INICIAR.bat`; el lanzador muestra la dirección y busca un puerto libre entre 8787 y 8796. No cierra otras copias. En `/health`, verificar `app_version`, `nlp_layers.presidio.available` y `nlp_layers.spacy.available`. Verificar también carga, análisis, agrupación y exportaciones con documentos ficticios.

Las pruebas de estructura del paquete se omiten antes de construirlo; después de construirlo deben ejecutarse sin omisiones. Para verificar otra carpeta, establecer `ANON_PKG_DIR`.

No distribuir documentos reales, equivalencias de usuarios, sesiones, bases de datos, registros, credenciales ni archivos de configuración personales. Los resultados de validación permanecen en `build/validation/`, fuera de Git y de la entrega.

Los informes de versiones anteriores están en [el archivo histórico](historico/README.md)
y no se distribuyen en el portable. Las copias locales anteriores se conservan
aparte de la entrega vigente, en `_archivo/releases/`, fuera de Git.

## Publicación y actualización

Publicar el código en Git y el ZIP como adjunto de una Release; nunca incorporar ejecutables o modelos al historial. Conservar `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.txt`, `LICENSES/` y la licencia del modelo. Revisar las condiciones de marca en [NOTICE](../NOTICE) antes de reutilizar el logo.

Para actualizar, extraer la nueva versión en otra carpeta y guardar las exportaciones antes de cerrar una sesión anterior. Las sesiones se mantienen en memoria y no migran entre procesos.

Ver [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), [COMPLIANCE.md](COMPLIANCE.md) y [MANUAL_INSTALACION.md](MANUAL_INSTALACION.md).
