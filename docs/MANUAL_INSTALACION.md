# Instalación — Anonimizador Judicial 3.4.9

Edición IALAB 3.4.9 de uso personal y académico. El portable para Windows
incluye el ejecutable y el modelo local. Para trabajar con el código fuente,
seguí [Desarrollo del anonimizador](DESARROLLO.md).

Hay dos formas de instalarla en Windows: el **portable ZIP**, disponible hoy,
y la aplicación de **Microsoft Store**, en preparación. Las dos procesan los
documentos en tu equipo y se pueden tener instaladas a la vez.

## Instalar desde Microsoft Store (en preparación)

La aplicación se va a llamar **Anonimizador de uso personal**. **Todavía no
está publicada**; cuando lo esté, el [README](../README.md) va a incluir el
enlace a su ficha. La instalación prevista es:

1. Abrir la ficha en Microsoft Store y pulsar **Obtener**.
2. Abrir **Anonimizador de uso personal** desde el menú Inicio.
3. La aplicación abre en su propia ventana. No hace falta extraer un ZIP ni
   ejecutar INICIAR.bat.

Diferencias con el portable:

- **Cerrar la ventana cierra la aplicación.** Antes de cerrar pide
  confirmación, porque el documento en revisión se descarta. Guardá primero
  tus exportaciones.
- Abrirla otra vez mientras está en uso trae al frente la ventana abierta; no
  inicia una segunda copia.
- Las actualizaciones llegan por Microsoft Store.
- Al exportar, Windows pregunta dónde guardar cada archivo.
- Requiere **Microsoft Edge WebView2**, incluido en Windows 11 y en Windows 10
  actualizado. Si falta, la aplicación avisa y se abre en el navegador; en ese
  caso cerrar la pestaña no la detiene.

Microsoft firma el paquete al certificarlo. Se espera que eso evite
[el bloqueo del Control Inteligente de Aplicaciones](#si-windows-bloquea-la-aplicación)
que afecta al portable; se va a confirmar con la aplicación ya publicada.

Qué guarda en el equipo: ver la [directiva de privacidad](../PRIVACY.md).

## Descargar y extraer el portable

El paquete para **Windows 10/11 de 64 bits** es
**AnonimizadorJudicial-3.4.9-Windows.zip**. Usá el enlace de descarga
del [README](../README.md). No requiere Python ni Internet para procesar
documentos; la preparación del entorno de desarrollo sí requiere descargas.

1. Descargá el ZIP del portable publicado en esta edición IALAB.
2. Clic derecho → **Extraer todo**. Elegí una carpeta nueva con permiso de
   escritura, por ejemplo Documentos\Anonimizador-IALAB-3.4.9.
3. Conservá la carpeta completa. No ejecutes el programa dentro del ZIP ni
   mezcles archivos _internal de versiones distintas.

El ZIP incluye el ejecutable, frontend, modelo local, manuales y licencias.
El tamaño y el SHA-256 se informan junto a la entrega.
**Code → Download ZIP** de GitHub contiene los fuentes, no el portable.
La carpeta local de compilación es `dist/AnonimizadorJudicial-NLP-3.4.9/`.
Usá una carpeta nueva para mantener intactas otras instalaciones.

## Iniciar y verificar

1. Abrí la carpeta extraída y ejecutá **INICIAR.bat**.
2. El navegador abre la dirección indicada al iniciar. Usa 127.0.0.1:8787
   o un puerto libre entre **8788 y 8796** si otra copia ocupa el primero.
3. La cabecera debe identificar **IALAB** e indicar **v3.4.9**, el estado de Presidio/spaCy y
   **Catálogos cargados**.

Repetir INICIAR.bat vuelve a la instancia de esa misma carpeta. Las otras
versiones siguen abiertas. Si el navegador no se abre, repetí el inicio o
consultá PUERTO_ACTUAL.txt dentro de esa carpeta. El archivo contiene solo
el número de puerto: si dice `8789`, abrí <http://127.0.0.1:8789>.

**VERIFICAR.bat** comprueba esa instancia, aunque use otro puerto. En /health:

- app_version: 3.4.9.
- nlp_layers.presidio.available: true.
- nlp_layers.spacy.available: true.
- nlp_layers.dictionaries: catálogos disponibles y cantidades cargadas.

Para usarla, consultá el archivo MANUAL_USUARIO.md incluido junto a este manual.

## Si Windows bloquea la aplicación

El aviso **«Control Inteligente de Aplicaciones ha bloqueado un archivo»**
significa que Windows detuvo la ejecución. La versión 3.4.9 del anonimizador
todavía no tiene firma digital y puede quedar bloqueada en Windows 11. Pulsá
**De acuerdo** y avisá a quien te compartió el programa; indicá qué archivo
intentaste abrir. Si es un equipo de trabajo, consultá a sistemas. Descargar
de nuevo el mismo ZIP no corrige este bloqueo. No desactives la protección
del equipo para usar esta versión.

Este aviso es distinto de **«Windows protegió tu PC»** (SmartScreen). No hay
una excepción por aplicación para el Control Inteligente de Aplicaciones.
El equipo de desarrollo debe publicar una entrega firmada y probarla en
Windows 11 con esa protección activada.

## Actualizar o cerrar

Para actualizar, guardá primero tus exportaciones. Extraé la nueva versión en
otra carpeta y abrila desde allí. Los documentos abiertos en la copia anterior
no se transfieren a la nueva; cada proceso tiene sesiones independientes.

Cerrar una pestaña del navegador puede dejar el programa funcionando. Para
cerrarlo completamente, guardá tus exportaciones y finalizá
AnonimizadorJudicial-NLP.exe desde el Administrador de tareas. Si hay varias
copias, verificá su ruta para elegir la que corresponde. Al terminar el proceso
se pierden sus sesiones en memoria.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| No abre el navegador | Repetí INICIAR.bat o abrí `http://127.0.0.1:PUERTO`, reemplazando PUERTO por el número de PUERTO_ACTUAL.txt. |
| Puerto ocupado | INICIAR.bat busca otro. Si los diez puertos están ocupados, guardá y cerrá una copia que no necesites. |
| Pantalla de una versión anterior | Iniciá desde la carpeta de la descarga nueva y verificá la versión en la cabecera. |
| Falta el ejecutable o un archivo interno | Volvé a extraer el ZIP completo; revisá si el antivirus puso un archivo en cuarentena. |
| Presidio o spaCy no disponibles | Volvé a extraer el paquete completo; deben conservarse _internal y models. |
| Catálogos incompletos | Volvé a extraer el ZIP completo. Si agregaste catálogos propios, revisá que cada archivo sea una lista JSON válida y no vacía, y reiniciá la aplicación. |
| No encuentra esta sesión | Cargá el documento otra vez: el proceso puede haberse cerrado o la página pertenecer a otra copia. |
| PDF escaneado | Usá un PDF con texto digital o Word. El reconocimiento de documentos escaneados (OCR) todavía no está disponible. |
| Archivo demasiado grande | El límite de carga es 40 MB. Dividilo o reducí su tamaño. |

## Privacidad y licencia

La aplicación procesa los documentos en tu equipo, conserva las sesiones solo
en memoria y no crea sessions.db. Los archivos que descargues se guardan
donde vos elijas. El CSV de equivalencias incluye los datos originales.

Conservá LICENSE, NOTICE, THIRD_PARTY_NOTICES.txt, LICENSES,
COMPLIANCE.md y models/es_core_news_md/LICENSE al compartir el portable.

## macOS

Este ZIP contiene un ejecutable Windows y no funciona en macOS. Todavía no
hay una entrega Mac de esta versión en `anonimizador_uso_personal`: necesita compilarse
y verificarse en ese sistema antes de publicarse.
