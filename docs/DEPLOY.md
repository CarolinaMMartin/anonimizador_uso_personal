# Construcción y distribución — 3.4.9

Esta edición IALAB se publica en `CarolinaMMartin/anonimizador_uso_personal`.
El portable Windows 3.4.9 se distribuye como
`AnonimizadorJudicial-3.4.9-Windows.zip`,
acompañado por su SHA-256. La carpeta local de compilación es
`dist/AnonimizadorJudicial-NLP-3.4.9/`.

Generar un ZIP local no publica una Release ni modifica las descargas
existentes. Los resultados de esta copia se registran en
[VERIFICACION_3.4.9.md](VERIFICACION_3.4.9.md). Los resultados históricos del
MPF no validan el nuevo paquete. macOS requiere construir y verificar un
paquete propio en ese sistema.

## Bloqueo de Windows 11 pendiente de resolver

La compilación 3.4.9 no está firmada. El Control Inteligente de Aplicaciones
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

El paquete de Microsoft Store es la vía prevista para resolverlo: la Store
firma el MSIX al certificarlo. Que una aplicación instalada desde la Store
funcione con el Control Inteligente de Aplicaciones activo es una hipótesis
que solo se puede comprobar con la aplicación ya publicada; es la primera
prueba a hacer después de la certificación.

## Paquete MSIX para Microsoft Store

El MSIX es una salida adicional del mismo build. No reemplaza al portable: se
arma a partir de la carpeta portable ya construida y no la modifica.

```powershell
.venv\Scripts\python scripts\build_portable_full.py
.venv\Scripts\python scripts\build_msix.py
$env:ANON_REQUIRE_MSIX = '1'
.venv\Scripts\python -m pytest tests/test_msix_manifest.py tests/test_msix_package.py -q
```

Resultado: la carpeta `build/msix/AnonimizadorUsoPersonal/` y el archivo
`dist/AnonimizadorUsoPersonal-3.4.9-x64.msix`, sin firmar. `build_msix.py`
necesita `makepri.exe` y `makeappx.exe` del Windows SDK; los busca en
`ANON_WINDOWS_SDK_BIN`, en el PATH y en el SDK instalado. Con `--layout-only`
arma y verifica solo la carpeta, sin el SDK. Con `--package` toma otra carpeta
portable.

El paquete lleva el ejecutable, `_internal` (con los diccionarios), `frontend`,
el modelo, las licencias, los tres PDF oficiales en `Manuales/`, el manifiesto y los íconos. No lleva `INICIAR.bat`,
`VERIFICAR.bat` ni `iniciar.ps1`: la Store inicia directamente el ejecutable, y
[app/launcher.py](../app/launcher.py) resuelve la instancia única y el puerto
libre. Con identidad de paquete la aplicación abre en ventana propia
([app/window.py](../app/window.py)) y escribe solo en
`%LOCALAPPDATA%\AnonimizadorUsoPersonal`.

### Identidad

El manifiesto se genera desde la plantilla
[packaging/msix/AppxManifest.xml](../packaging/msix/AppxManifest.xml). La
versión sale de `APP_VERSION` en cuatro partes: `3.4.9` pasa a `3.4.9.0`. Los
valores siguientes son los del producto reservado en Partner Center; si no
coinciden exactamente, la Store rechaza el paquete.

| Campo | Valor |
|---|---|
| `Identity/@Name` | `CarolinaMartin.Anonimizadordeusopersonal` |
| `Identity/@Publisher` | `CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231` |
| `Properties/PublisherDisplayName` | `Carolina Martin` |
| `Properties/DisplayName` | `Anonimizador de uso personal` |

El idioma del recurso es `es-AR`. Confirmar al crear la ficha que el idioma de
la descripción en Partner Center coincide.

### Íconos

El logo de la aplicación es [packaging/app.ico](../packaging/app.ico), con
versiones dibujadas de 16 a 256 px. Lo usan el ejecutable (PyInstaller lo
incrusta en Windows y la ventana propia lo toma de ahí) y el paquete de Store:
`packaging/msix/Assets/` se genera con `python scripts/make_msix_icons.py` a
partir de ese archivo, y una prueba falla si las dos cosas dejan de coincidir.
Para cambiarlo, reemplazar `app.ico` y volver a correr el script; también
acepta `--source` con otro ICO o PNG de fondo transparente.

La interfaz conserva el logo y la identidad de IALAB en el encabezado; el
logo de la aplicación no es una marca institucional. Sobre una barra de tareas
oscura el cuerpo azul del logo contrasta poco: se distinguen las líneas blancas
y la franja verde.

### Red de la ventana (WebView2)

La ventana solo muestra `127.0.0.1`, pero el motor de WebView2 abre por su
cuenta conexiones a servidores de Microsoft.
[app/webview_hardening.py](../app/webview_hardening.py) lo arranca con esas
funciones desactivadas y deriva a un proxy inexistente los pedidos del motor
que no sean a la propia máquina. Eso elimina la descarga de configuración y
componentes, pero no todo: queda una conexión intermitente a los servicios de
identidad de Microsoft. Qué se midió, qué opción funciona y qué no puede
controlar la aplicación está en
[VERIFICACION_RED_WEBVIEW2.md](VERIFICACION_RED_WEBVIEW2.md). No afirmar en la
ficha de la Store que la aplicación no realiza ninguna conexión.
Repetir esa medición al cambiar la versión de pywebview o cuando una versión
nueva del runtime de WebView2 cambie el comportamiento.

### Prueba local antes de enviar

1. Activar el modo de desarrollador de Windows.
2. Registrar el paquete sin firmar desde la carpeta armada:
   `Add-AppxPackage -Register build\msix\AnonimizadorUsoPersonal\AppxManifest.xml`
3. Abrir la aplicación desde el menú Inicio y recorrer el flujo completo con
   [el escrito de ejemplo](ejemplos/escrito_ficticio.docx): cargar, analizar,
   revisar, exportar en todos los formatos y cerrar la ventana. Confirmar en el
   Administrador de tareas que el proceso terminó.
4. Abrirla dos veces y confirmar que queda un solo proceso.
5. Confirmar que no se escribió nada en la carpeta de instalación.
6. Desconectar la red y repetir el paso 3: la aplicación debe funcionar igual.
7. Correr el Kit de certificación de aplicaciones en Windows sobre el `.msix`.

Sin registrar el paquete, la ventana propia se puede probar sobre el portable
o el código fuente definiendo `ANON_WINDOW=1` antes de iniciar el ejecutable.

### Envío

El workflow de release arma el MSIX después de verificar el portable y lo sube
como artefacto `anonimizador-msix-VERSION`. No lo adjunta a la Release de
GitHub. El envío se hace a mano desde Partner Center, con la
[directiva de privacidad](../PRIVACY.md) como URL de privacidad y el escrito
de ejemplo en las notas de certificación. `runFullTrust` es una capacidad
restringida: Partner Center pide justificarla (la aplicación es un programa de
escritorio que ejecuta un servidor local y un modelo de lenguaje incluido).

## Construcción

Desde la raíz del repositorio, con Python 3.12–3.13:

Usar un entorno virtual aislado, sin `--system-site-packages`; no reutilizar
dependencias heredadas de otra instalación de Python.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
$env:ANON_PKG_DIR = 'dist/AnonimizadorJudicial-NLP-3.4.9'
.venv\Scripts\python -m pytest tests -q
node --test tests/frontend_session.test.cjs
.venv\Scripts\python scripts\audit_repository.py
.venv\Scripts\python scripts\build_portable_full.py --output dist/AnonimizadorJudicial-NLP-3.4.9
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python scripts\check_windows_launcher.py --package dist/AnonimizadorJudicial-NLP-3.4.9 --keep-running
$appPort = Get-Content -LiteralPath 'dist/AnonimizadorJudicial-NLP-3.4.9/PUERTO_ACTUAL.txt'
.venv\Scripts\python scripts\portable_smoke.py --package dist/AnonimizadorJudicial-NLP-3.4.9 --port $appPort --use-existing --category-cases --all-categories
.venv\Scripts\python scripts\check_sensitive_portable.py --package dist/AnonimizadorJudicial-NLP-3.4.9 --port $appPort
.venv\Scripts\python scripts\check_identity_flow.py --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\check_identity_flow.py --caption-cases --url "http://127.0.0.1:$appPort"
.venv\Scripts\python scripts\package_release.py --package dist/AnonimizadorJudicial-NLP-3.4.9 --output dist/AnonimizadorJudicial-3.4.9-Windows.zip
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
