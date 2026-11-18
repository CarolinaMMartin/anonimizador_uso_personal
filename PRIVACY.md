# Directiva de privacidad — Anonimizador de uso personal

Última actualización: noviembre de 2026.

Esta directiva describe qué hace la aplicación **Anonimizador de uso personal**
con tus documentos y datos. Vale para el paquete de Microsoft Store y para el
portable ZIP para Windows.

## En pocas palabras

- Tus documentos se procesan **en tu computadora**. La aplicación no los envía
  a ningún servidor.
- No hay cuentas, registro, publicidad, analíticas ni telemetría propias de la
  aplicación.
- La aplicación no recopila ni comparte datos personales con quien la
  desarrolla ni con terceros.

## Qué datos trata la aplicación

Los documentos Word (.docx) y PDF que cargás, y los datos personales que
contengan: nombres, números de documento, domicilios, teléfonos y otros. La
aplicación los lee para detectar esos datos y reemplazarlos por etiquetas.

Ese tratamiento ocurre en la memoria del programa. El documento cargado, el
análisis y tus decisiones de revisión **se pierden al cerrar la aplicación**:
no se guardan en una base de datos ni en archivos de sesión.

## Qué se guarda en tu equipo

- **Los archivos que exportás** (Word, PDF, Markdown o CSV), en la carpeta que
  elijas al descargarlos. Quedan bajo tu control.
- **Un archivo con un número de puerto** (`PUERTO_ACTUAL.txt`), que la
  aplicación usa para encontrarse a sí misma si la abrís dos veces. No contiene
  datos personales. En el paquete de Store está en
  `%LOCALAPPDATA%\AnonimizadorUsoPersonal`; en el portable, en la carpeta
  donde lo extrajiste.
- **Datos temporales de la ventana**, en el paquete de Store. La ventana
  funciona en modo privado, sin cookies ni almacenamiento persistentes, y sus
  archivos temporales se eliminan al cerrarla. Si el equipo se apaga o la
  aplicación se interrumpe de forma abrupta, pueden quedar restos en la
  subcarpeta `webview` de la carpeta anterior; podés borrarla.

La **tabla de equivalencias (CSV)** que podés exportar contiene los datos
originales junto a sus etiquetas. Guardala de forma privada: quien la tenga
puede revertir la anonimización.

## Conexiones de red

La interfaz se sirve desde tu propio equipo, en la dirección local
`127.0.0.1`, que no es accesible desde otras computadoras. El análisis usa un
modelo de lenguaje y catálogos incluidos en la instalación; no consulta
servicios en línea. Las fuentes y demás recursos de la interfaz también están
incluidos.

La aplicación funciona sin conexión a Internet.

## Componentes de Microsoft

Dos componentes ajenos a este proyecto intervienen cuando usás el paquete de
Microsoft Store. Se rigen por la
[Declaración de privacidad de Microsoft](https://privacy.microsoft.com/privacystatement):

- **Microsoft Store** instala y actualiza la aplicación. Microsoft conoce la
  instalación y puede generar estadísticas de uso y de errores según la
  configuración de diagnóstico de tu Windows. Esos datos no incluyen el
  contenido de tus documentos.
- **Microsoft Edge WebView2** es el componente de Windows que dibuja la
  ventana. La aplicación solo le pide mostrar la dirección local `127.0.0.1`.
  WebView2 es mantenido y actualizado por Microsoft y puede comunicarse con
  sus servidores por funciones propias, como su actualización. Este proyecto
  no controla ese comportamiento.

El portable ZIP no usa estos componentes: se abre en el navegador que tengas
configurado, que se rige por sus propias condiciones.

## Menores

La aplicación no está dirigida a menores y no recopila datos de ninguna
persona usuaria.

## Tus responsabilidades

La detección automática puede omitir datos o marcar de más. Revisá siempre el
documento exportado antes de compartirlo. Usá la aplicación con documentos que
tengas derecho a tratar.

## Cambios en esta directiva

Los cambios se publican en este archivo, con su fecha, en el repositorio del
proyecto.

## Contacto

Para consultas sobre privacidad o para informar un problema, usá los canales
indicados en [SECURITY.md](SECURITY.md). No incluyas documentos reales ni datos
personales en el reporte.
