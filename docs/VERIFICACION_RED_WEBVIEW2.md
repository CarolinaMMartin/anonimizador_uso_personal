# Red de la ventana propia (WebView2) — medición

Medido el 18 de noviembre de 2026 en una máquina con Windows 11, runtime de
Microsoft Edge WebView2 157.0.4341.60, pywebview 6.2.1 (SDK de WebView2
1.0.3856.49) y datos de diagnóstico de Windows en nivel «opcionales».

Aplica a la ventana propia del paquete de Microsoft Store. El portable ZIP se
abre en el navegador de cada persona y no usa WebView2.

## Qué se quería saber

La ventana solo muestra `http://127.0.0.1`. La pregunta es si el motor de
WebView2 abre, por su cuenta, conexiones hacia afuera del equipo, y qué
opciones de arranque lo evitan de verdad.

## Qué dice la documentación de Microsoft

Consultada el mismo día en Microsoft Learn.

| Función | Qué puede hacer la aplicación | Fuente |
|---|---|---|
| SmartScreen (comprobación de seguridad en línea) | Apagarlo con `CoreWebView2Settings.IsReputationCheckingRequired = false` | [Data and privacy in WebView2](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/data-privacy) |
| Volcados de fallos | Evitar el envío con `CoreWebView2EnvironmentOptions.IsCustomCrashReportingEnabled = true` | misma página |
| Datos de diagnóstico | **Nada.** «The data collection consent for WebView2 is governed by the … Diagnostic data setting» de Windows, y los datos obligatorios se recopilan siempre | misma página |
| Actualización del runtime | **Nada.** La hace el servicio Microsoft Edge Update, fuera del proceso; solo la puede desactivar quien administra el equipo | [Distribute your app and the WebView2 Runtime](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |
| Red en segundo plano y actualización de componentes | No hay opción documentada | [WebView2 browser flags](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags) |

La página de flags documenta `--proxy-server` y `--no-first-run`, entre otros,
y advierte: «Apps in production shouldn't use WebView2 browser flags, because
these flags might be removed or altered at any time». Los flags de Chromium
`--disable-background-networking`, `--disable-component-update`,
`--disable-domain-reliability`, `--disable-sync`, `--no-pings`,
`--disable-client-side-phishing-detection` y `--disable-breakpad` **no figuran**
en la documentación de Microsoft.

No existe una receta oficial para una aplicación WebView2 sin red.

## Cómo se midió

Se abrió la aplicación en modo ventana desde el código fuente, con una carpeta
de datos nueva. A los 15 segundos se cargó y analizó por la API el
[escrito de ejemplo](ejemplos/escrito_ficticio.docx). Durante toda la corrida,
aproximadamente una vez por segundo, se listaron las conexiones TCP
(`Get-NetTCPConnection`) del proceso del servidor y de todos los procesos
`msedgewebview2.exe` que usaban esa carpeta de datos, descartando las de
loopback.

Los destinos se identificaron por el certificado TLS que presenta cada
dirección; el contenido de las conexiones no se pudo observar.

## Resultados

Hubo dos familias de destinos, las dos de Microsoft:

- **Distribución de contenido** (`*.azureedge.net`, 150.171.x.x), desde el
  servicio de red del motor. Coincide con la aparición del proceso
  `Unzipper`: el motor baja y descomprime configuración y componentes.
- **Servicios de identidad de Microsoft 365** (certificado `outlook.com`, que
  cubre `*.office.com`; 52.97.x.x y 52.123.x.x), casi siempre desde el
  proceso principal del motor.

Desde el código fuente, una corrida por configuración:

| Configuración | Duración | Distribución de contenido | Identidad de Microsoft 365 | `Unzipper` |
|---|---|---|---|---|
| Sin ajustes (como abre pywebview) | 300 s | 2 destinos | 1 | sí |
| Solo las API documentadas (SmartScreen y volcados) | 255 s | 1 | 2 | sí |
| Solo `--proxy-server` a un proxy inexistente | 255 s | 0 | 0 | no |
| Solo los flags de Chromium | 255 s | 0 | 0 | no |
| Todo junto (lo que usa la aplicación) | 300 s | 0 | 0 | no |

Con el ejecutable compilado y todo aplicado, ocho corridas de entre 110 y
240 segundos:

| | Distribución de contenido | Identidad de Microsoft 365 | `Unzipper` |
|---|---|---|---|
| 4 corridas con la configuración que usa la aplicación | 0 en las 4 | **1 conexión en 2 de las 4** | nunca |
| 4 corridas agregando `--allow-browser-signin=false` | 0 en las 4 | **1 conexión en 2 de las 4** | nunca |

El proceso del servidor (Python) no abrió ninguna conexión externa en ninguna
corrida.

Conclusiones:

- Sin ajustes, WebView2 **sí** se comunica con Microsoft aunque la aplicación
  solo le pida mostrar la dirección local.
- Las API documentadas, solas, no reducen esas conexiones. Se aplican igual:
  son las únicas con respaldo oficial y cubren lo que se enviaría ante un
  fallo o una descarga, que esta prueba no provoca. En la línea de comandos
  del motor se comprobó que la opción de volcados toma efecto
  (`--edge-webview-disable-crash-reporting=1`).
- El proxy inexistente y los flags de Chromium **eliminan la descarga de
  configuración y componentes**: no volvió a aparecer en ninguna corrida.
- **Queda una conexión que la aplicación no logra evitar.** En la mitad de
  las corridas con el ejecutable compilado, el proceso principal del motor
  abre una única conexión HTTPS a los servicios de identidad de Microsoft 365,
  entre los 19 y los 77 segundos. Sale del proceso principal y no del servicio
  de red, es decir, por fuera de la pila de red de Chromium: por eso el proxy
  y los flags no la alcanzan. Se probó además `--allow-browser-signin=false`:
  con ese interruptor, 2 de 4 corridas la siguieron mostrando, y se descartó.
- La hipótesis es que el motor de Edge consulta el perfil de la cuenta con la
  que se inició sesión en Windows. **No está confirmada**: no se pudo ver el
  nombre de host ni el contenido. Lo que se le pide al motor es solo la
  dirección local, y los documentos cargados nunca salen del proceso del
  servidor; pero qué envía el motor en esa conexión no se verificó.
- Que las corridas desde el código fuente con todo aplicado dieran cero puede
  ser azar: fueron pocas. No hay evidencia de que el ejecutable compilado se
  comporte distinto.

## Qué hace la aplicación

[app/webview_hardening.py](../app/webview_hardening.py), antes de crear la
ventana:

1. Apaga SmartScreen, el autocompletado y el guardado de contraseñas, y crea
   el entorno de WebView2 con el envío de volcados desactivado.
2. Deriva todo pedido HTTP/HTTPS que no sea a la propia máquina a
   `127.0.0.1:9`, donde no hay nada escuchando. Las direcciones de loopback
   quedan exceptuadas, y por eso la interfaz carga.
3. Agrega los flags de Chromium listados arriba.

Si alguna capa no se puede aplicar, queda registrada y la ventana abre con las
demás.

## Qué opciones quedan para la conexión restante

Ninguna está implementada; son decisiones a tomar.

- **Aceptarla y declararla** en la directiva de privacidad: el componente de
  Microsoft que dibuja la ventana puede contactar a servicios de Microsoft
  aunque la aplicación le desactive la red en segundo plano.
- **Distribuir el runtime en versión fija** junto con la aplicación (más de
  250 MB adicionales). Da control sobre la versión, pero no hay evidencia de
  que cambie este comportamiento.
- **No usar ventana propia** y abrir el navegador de la persona, como el
  portable. Elimina WebView2, pero se pierde el cierre de la aplicación al
  cerrar la ventana, y el navegador tiene su propio tráfico.
- **Un cortafuegos del equipo o de la organización** que bloquee la salida de
  `msedgewebview2.exe`. Es la única forma de garantizar cero, requiere
  permisos de administrador y afecta a todas las aplicaciones que usan
  WebView2.

## Límites de esta medición

- Es un muestreo de conexiones TCP, no una captura de tráfico: una conexión
  que dure menos de un segundo puede no verse, y no se observaron UDP ni
  consultas DNS. Una captura completa necesita permisos de administrador.
- Pocas corridas de pocos minutos, una máquina, una versión del runtime. El
  runtime se actualiza solo y su comportamiento puede cambiar. La máquina
  tenía una VPN activa y una cuenta de Windows con sesión iniciada; en otra
  configuración el resultado puede diferir.
- No cubre al servicio **Microsoft Edge Update** ni la telemetría propia de
  **Windows**: son otros procesos del sistema, existen con o sin esta
  aplicación y no se pueden controlar desde ella.
- No cubre a **Microsoft Store**, que instala y actualiza el paquete.
- Se midió desde el código fuente y con el ejecutable compilado, con
  `ANON_WINDOW=1`; no con el paquete instalado desde la Store.
- La carga del documento se hizo por la API; nadie recorrió la interfaz a
  mano durante la medición.

## Prueba manual sin conexión

Pendiente de hacer por una persona, mirando la interfaz.

1. Con el paquete registrado (ver
   [DEPLOY.md](DEPLOY.md#prueba-local-antes-de-enviar)) o, sin registrarlo,
   definiendo `ANON_WINDOW=1` y abriendo `AnonimizadorJudicial-NLP.exe`.
2. Desconectar el wifi y cualquier cable de red. Una VPN activa se va a caer.
3. Abrir la aplicación. Debe abrir la ventana y mostrar el motor local
   disponible.
4. Cargar el [escrito de ejemplo](ejemplos/escrito_ficticio.docx), analizar,
   revisar, agregar una detección manual y abrir el editor.
5. Exportar en todos los formatos: Word, PDF, Markdown y la tabla de
   equivalencias en CSV. Abrir cada archivo exportado.
6. Cerrar la ventana y confirmar en el Administrador de tareas que el proceso
   terminó.
7. Volver a conectar la red.

Cualquier paso que falle sin conexión y funcione con conexión es un defecto.

## Cómo repetir la medición

Repetirla al cambiar la versión de pywebview o si una versión nueva del
runtime cambia el comportamiento. Con la aplicación abierta en modo ventana:

```powershell
$carpeta = "$env:LOCALAPPDATA\AnonimizadorUsoPersonal"   # o la de ANON_DATA_DIR
$ids = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" |
         Where-Object { $_.CommandLine -like "*$carpeta*" } |
         ForEach-Object { [int]$_.ProcessId })
Get-NetTCPConnection | Where-Object {
    $ids -contains $_.OwningProcess -and
    $_.RemoteAddress -notin '127.0.0.1', '::1', '0.0.0.0', '::' }
```

Repetir el último comando durante varios minutos. No debe aparecer ninguna
dirección de `*.azureedge.net`; puede aparecer la conexión a los servicios de
identidad descrita arriba. La línea de comandos del proceso principal de
WebView2 debe incluir `--proxy-server=http://127.0.0.1:9`.
