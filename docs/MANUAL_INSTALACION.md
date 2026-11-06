# Instalación — Anonimizador Judicial 3.4.3

Aplicación portable de uso personal/académico. Esta entrega se verifica en
**Windows 10/11 de 64 bits**. No requiere instalar Python ni conectarse a
Internet para procesar documentos. En general no requiere administrador;
pueden existir restricciones propias de tu equipo u organización.

## Descargar y extraer

[**Descargar para Windows — versión 3.4.3 con las correcciones de revisión**](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/download/v3.4.3/AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip).

1. Descargá **AnonimizadorJudicial-3.4.3-revision-egm-Windows.zip**.
2. Clic derecho → **Extraer todo**. Elegí una carpeta nueva con permiso de
   escritura, por ejemplo Documentos\Anonimizador-3.4.3.
3. Conservá la carpeta completa. No ejecutes el programa dentro del ZIP ni
   mezcles archivos _internal de versiones distintas.

El ZIP incluye el ejecutable, frontend, modelo local, manuales y licencias.
El tamaño y el SHA-256 de la descarga se informan junto a la entrega.
**Code → Download ZIP** de GitHub contiene los fuentes, no el portable.
La descarga vigente está en la [Release 3.4.3 de anonimizador_mpf](https://github.com/CarolinaMMartin/anonimizador_mpf/releases/tag/v3.4.3).
El sufijo `revision-egm` identifica el paquete con las correcciones posteriores
a la primera entrega local 3.4.3. Si trabajás desde el proyecto, esa copia está
en `dist/AnonimizadorJudicial-NLP-3.4.3-revision-egm/`.

## Iniciar y verificar

1. Abrí la carpeta extraída y ejecutá **INICIAR.bat**.
2. El navegador abre la dirección indicada al iniciar. Usa 127.0.0.1:8787
   o un puerto libre entre **8788 y 8796** si otra copia ocupa el primero.
3. La cabecera debe indicar **v3.4.3**, el estado de Presidio/spaCy y
   **Catálogos cargados**.

Repetir INICIAR.bat vuelve a la instancia de esa misma carpeta. Las otras
versiones siguen abiertas. Si el navegador no se abre, repetí el inicio o
consultá PUERTO_ACTUAL.txt dentro de esa carpeta. El archivo contiene solo
el número de puerto: si dice `8789`, abrí <http://127.0.0.1:8789>.

**VERIFICAR.bat** comprueba esa instancia, aunque use otro puerto. En /health:

- app_version: 3.4.3.
- nlp_layers.presidio.available: true.
- nlp_layers.spacy.available: true.
- nlp_layers.dictionaries: catálogos disponibles y cantidades cargadas.

Para usarla, consultá el archivo MANUAL_USUARIO.md incluido junto a este manual.

## Si Windows bloquea la aplicación

El aviso **«Control Inteligente de Aplicaciones ha bloqueado un archivo»**
significa que Windows detuvo la ejecución. La versión 3.4.3 del anonimizador
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
| PDF escaneado | Usá un PDF con texto digital o Word. Esta versión no incluye OCR. |
| Archivo demasiado grande | El límite de carga es 40 MB. Dividilo o reducí su tamaño. |

## Privacidad y licencia

La aplicación procesa los documentos en tu equipo, conserva las sesiones solo
en memoria y no crea sessions.db. Los archivos que descargues se guardan
donde vos elijas. El CSV de equivalencias incluye los datos originales.

Conservá LICENSE, NOTICE, THIRD_PARTY_NOTICES.txt, LICENSES,
COMPLIANCE.md y models/es_core_news_md/LICENSE al compartir el portable.

## macOS

Este ZIP contiene un ejecutable Windows y no funciona en macOS. Todavía no
hay una entrega Mac de esta versión en `anonimizador_mpf`: necesita compilarse
y verificarse en ese sistema antes de publicarse.
