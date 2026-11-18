# Plan: publicar el anonimizador en Microsoft Store (MSIX)

Documento de trabajo para Claude Code. Describe qué hay que cambiar en este
repositorio para generar un paquete MSIX apto para Microsoft Store, además del
portable ZIP que ya existe.

## Objetivo

Que una persona sin conocimientos técnicos instale la app desde Microsoft Store,
le quede el ícono en el menú Inicio y la use sin GitHub, sin ZIP y sin
`INICIAR.bat`. La Store firma el paquete MSIX, lo que evita el bloqueo del
Control Inteligente de Aplicaciones de Windows 11 que hoy afecta al portable sin
firma (ver `docs/DEPLOY.md`).

## Alcance de esta etapa

Incluye: lanzador en Python, carpeta de datos del usuario, ventana propia,
manifiesto e íconos MSIX, paso de empaquetado en CI y documento de ejemplo.

No incluye: OCR. Va en una etapa posterior, como primera actualización. Solo se
deja preparado el punto de enganche (tarea 6).

## Restricciones

- El portable ZIP actual tiene que seguir construyéndose y pasando sus pruebas.
  El MSIX es una salida adicional del mismo build, no un reemplazo.
- Respetar los controles existentes: `scripts/audit_repository.py`,
  `scripts/build_provenance.py`, las pruebas de `tests/` y el inventario de
  licencias. Si un cambio los rompe, actualizar el control de forma coherente,
  no desactivarlo.
- Mantener la promesa de privacidad: servidor solo en `127.0.0.1`, sin llamadas
  externas, sin telemetría, sesiones solo en memoria.
- Trabajar en una rama nueva y abrir un pull request. No publicar releases.
- Este entorno de build es Windows. Lo que no se pueda probar localmente, decirlo
  de forma explícita en el PR en lugar de darlo por verificado.

## Identidad del producto (Partner Center)

Valores reales del producto ya reservado. Tienen que coincidir exactamente en el
manifiesto o la Store rechaza el paquete.

| Campo del manifiesto | Valor |
|---|---|
| `Identity/@Name` | `CarolinaMartin.Anonimizadordeusopersonal` |
| `Identity/@Publisher` | `CN=54101CBA-F9F0-4A60-A1F4-FA1225FEC231` |
| `Properties/PublisherDisplayName` | `Carolina Martin` |
| `Properties/DisplayName` | `Anonimizador de uso personal` |

Otros datos, solo de referencia:

- Package Family Name: `CarolinaMartin.Anonimizadordeusopersonal_54x6cpnse2wsy`
- Id. de Store: `9PM0PCV9ZJ3X`

## Tareas

### 1. Lanzador en Python

Hoy `scripts/windows/iniciar.ps1` resuelve tres cosas que un paquete de Store no
puede delegar en un script: instancia única, búsqueda de puerto libre entre 8787
y 8796, y verificación por `/health` de que la instancia encontrada es de la
misma versión y carpeta. Un MSIX arranca directamente el `.exe`.

- Llevar esa lógica a `scripts/launcher.py` (o a un módulo en `app/`).
- Si ya hay una instancia viva de la misma versión, traerla al frente o reabrir
  su ventana en lugar de iniciar otra.
- `INICIAR.bat`, `VERIFICAR.bat` e `iniciar.ps1` siguen existiendo para el
  portable, pero no se incluyen en el MSIX.

### 2. Carpeta de datos del usuario

La carpeta de instalación de una app de Store es de solo lectura.
`app/runtime_paths.py` define `app_dir()` como "carpeta del .exe (datos
persistentes: sesiones, logs)" y el lanzador escribe `PUERTO_ACTUAL.txt` junto al
ejecutable.

- Agregar una función para la carpeta de datos del usuario
  (`%LOCALAPPDATA%\AnonimizadorUsoPersonal` o equivalente) y usarla para todo lo
  que se escribe: archivo de puerto, logs y cualquier otro archivo de estado.
- Revisar todo el código en busca de escrituras relativas a `app_dir()`.
- Lo que solo se lee (frontend, diccionarios, `models/es_core_news_md`) queda
  donde está.
- En modo portable se puede conservar el comportamiento actual si las pruebas lo
  exigen; en modo empaquetado (MSIX) hay que usar siempre la carpeta de datos.

### 3. Ventana propia

Hoy `run_server()` en `app/main.py` abre el navegador con `webbrowser.open`, y
cerrar la pestaña deja el proceso vivo.

- Mostrar el frontend en una ventana propia con `pywebview` (usa WebView2 en
  Windows). Uvicorn corre en un hilo; al cerrar la ventana se detiene el servidor
  y termina el proceso.
- Título de la ventana y de la interfaz: `Anonimizador de uso personal`.
- Verificar que las descargas de exportación (Word, PDF, CSV, Markdown) funcionan
  dentro de la ventana. En pywebview las descargas hay que habilitarlas de forma
  explícita; confirmar el mecanismo vigente en su documentación.
- Si WebView2 no está disponible, caer al comportamiento actual (navegador) con
  un mensaje claro, en vez de fallar.
- Fijar la versión de `pywebview` en `requirements.txt`, sumar los hooks de
  PyInstaller que necesite y actualizar el inventario de licencias.

### 4. Manifiesto e íconos MSIX

- Crear `packaging/msix/AppxManifest.xml` como plantilla, con la versión
  inyectada desde `APP_VERSION` de `app/config.py`.
- Versión de cuatro partes: `3.4.4` pasa a `3.4.4.0`. La Store exige que la
  cuarta parte sea `0`.
- `ProcessorArchitecture="x64"`, `TargetDeviceFamily Name="Windows.Desktop"`.
- Aplicación de escritorio de confianza total:
  `EntryPoint="Windows.FullTrustApplication"` y la capacidad restringida
  `runFullTrust`.
- Idioma del recurso: español.
- Íconos generados desde `docs/marca/logos/isotype_azul.png`, en los tamaños que
  pide el manifiesto (logo de la tienda, 44x44, 150x150 y las variantes
  `targetsize` sin placa para la barra de tareas). Guardar el script que los
  genera para poder regenerarlos.
- Confirmar el esquema y los tamaños exactos contra la documentación vigente de
  Microsoft antes de darlos por buenos.

Pendiente de decisión de la autora: el uso del isotipo IALAB bajo una cuenta
personal de la Store. Dejar los íconos en una carpeta fácil de reemplazar.

### 5. Empaquetado en CI

- Agregar a `.github/workflows/release-windows.yml` un paso posterior a
  `build_portable_full.py` que arme la carpeta del paquete (ejecutable,
  `_internal`, frontend, diccionarios, modelo, licencias, manifiesto e íconos,
  sin los `.bat` ni `.ps1`) y la empaquete con `makeappx.exe pack` del Windows
  SDK del runner.
- Subir el `.msix` como artefacto del workflow. No hace falta firmarlo: la Store
  lo firma al certificarlo.
- Idealmente, encapsular esto en `scripts/build_msix.py` para poder correrlo
  también en local.
- Sumar pruebas de estructura del paquete MSIX en el mismo estilo que
  `tests/test_package_structure.py`: manifiesto válido, identidad correcta,
  versión coherente con `APP_VERSION`, ausencia de scripts `.bat`/`.ps1`.

### 6. Punto de enganche para OCR (sin implementarlo)

`app/extraction/pdf.py` ya recorre el PDF página por página y omite las que no
tienen texto.

- Reorganizar `extract_pdf` para que las páginas sin texto pasen por una función
  separada que hoy no hace nada, de modo que sumar OCR después no obligue a tocar
  el resto.
- Cuando el PDF es solo imagen, el mensaje al usuario debe decir que el
  reconocimiento de documentos escaneados todavía no está disponible.
- No agregar dependencias de OCR en esta etapa.

### 7. Documento de ejemplo

- Crear un `.docx` con un escrito judicial corto y totalmente ficticio (nombres,
  DNI, CUIT, domicilios y número de expediente inventados) en
  `docs/ejemplos/`.
- Sirve para las notas de certificación de la Store, para las capturas de la
  ficha y como prueba manual.

### 8. Documentación

- Actualizar `README.md`, `docs/MANUAL_INSTALACION.md` y `docs/DEPLOY.md` con el
  nuevo canal de instalación, aclarando que el portable sigue disponible.
- Agregar `PRIVACY.md` en la raíz con la directiva de privacidad.

## Prueba local antes de enviar a la Store

1. Activar el modo de desarrollador de Windows.
2. Registrar el paquete sin firmar desde la carpeta armada:
   `Add-AppxPackage -Register <carpeta>\AppxManifest.xml`
3. Abrir la app desde el menú Inicio y recorrer el flujo completo: cargar el
   documento de ejemplo, analizar, revisar, exportar en todos los formatos y
   cerrar la ventana. Confirmar en el Administrador de tareas que el proceso
   terminó.
4. Confirmar que no se escribió nada en la carpeta de instalación.
5. Correr el Kit de certificación de aplicaciones en Windows sobre el `.msix`.

## Criterios de aceptación

- El workflow genera el ZIP portable y el `.msix`, y todas las pruebas pasan.
- La app instalada como paquete abre en ventana propia, funciona sin conexión y
  termina al cerrar la ventana.
- Abrirla dos veces no deja dos procesos.
- El manifiesto coincide con la identidad de Partner Center.
- El PR lista qué se verificó en una máquina real y qué quedó sin probar.

## Hipótesis a validar después de publicar

Que una app instalada desde la Store funciona en Windows 11 con el Control
Inteligente de Aplicaciones activo. Solo se puede comprobar con la app ya
publicada; es la primera prueba a hacer tras la certificación.
