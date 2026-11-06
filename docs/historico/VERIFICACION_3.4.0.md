# Verificación de 3.4.0

> Registro histórico de esa entrega. Para instalar la versión vigente,
> consultar el [README](../../README.md); estos resultados no validan otra versión.

Registro de validación de la entrega local para Windows x64, 5 de noviembre
de 2026. Esta revisión incluye las correcciones de anonimización y la
adaptación visual MPF. Los documentos de prueba son sintéticos y no
representan datos reales.

## Código y recursos

- Suite Python: **638 pruebas y 765 subpruebas aprobadas**, sin omisiones.
- Frontend: **24 pruebas aprobadas**.
- Auditoría del repositorio: **158 archivos**, incluidos 107 archivos Python,
  4 JSON y 36 enlaces; **sin errores**.
- Dependencias: `pip check` correcto en el entorno de compilación.
- Formato de cambios: `git diff --check` sin errores.

Las regresiones cubren identificadores sensibles, límites completos de
personas y domicilios, denominaciones de organismos, carga de catálogos y
exportaciones. Incluyen los casos de sobrecaptura de palabras del relato
como parte de un nombre detectados durante la validación del portable.

## Ejecutable portable

Compilación final completada correctamente para Windows x64. El ejecutable
informa la versión **3.4.0** y carga Presidio, spaCy y el modelo local
`es_core_news_md`. Los catálogos cargados contienen **236 nombres, 342
apellidos y 16 expresiones regulares**.

- Lanzador: **7 de 7** comprobaciones aprobadas.
- Estructura del portable: **6 de 6** comprobaciones aprobadas.
- Categorías: **18 de 18** comprobaciones aprobadas.
- Agrupación: **23 de 23** comprobaciones aprobadas en cada modo: solo
  personas y todas las categorías.
- Correcciones manuales: **6 de 6** comprobaciones aprobadas.
- Partes de Word: **6 de 6** comprobaciones aprobadas en ambos modos,
  incluidos párrafos, tablas y prosa de encabezados y pies.
- Cancelación: **2 de 2** comprobaciones aprobadas; respuesta en **0,188 s**
  en esta ejecución.

La prueba integral de datos sensibles aprobó la carga de catálogos, las
11 categorías y las entradas DOCX y PDF. Se verificaron la vista previa
y el texto leído de las exportaciones Word y PDF: no conservaban los datos
sensibles sintéticos del caso. Las denominaciones de organismos y los
domicilios se reemplazaron completos.

Los recursos de la interfaz coinciden por SHA-256 entre el código fuente,
la copia del portable y los archivos embebidos en el ejecutable.

## Interfaz

No se realizó una revisión visual en navegador: las herramientas de
automatización del navegador no estuvieron disponibles. Por ello, no se
registra una validación visual de los tamaños de pantalla, el logo, la
paleta ni el recorrido completo de la interfaz. Las pruebas del frontend
comprueban comportamiento programático; no sustituyen esa inspección.

La referencia visual es el paquete `marca-mpf` suministrado para esta entrega.
Su propio documento describe colores, tipografía y logo relevados del sitio
del MPF en octubre de 2026; no se presenta como un manual oficial del organismo.

## Paquete de entrega

Paquete: `AnonimizadorJudicial-3.4.0-Windows.zip`.

- Comprobaciones CRC y SHA-256 correctas.
- Extracción completa, sin sesiones ni archivos de ejecución
  temporal. La ruta más larga de la carpeta de prueba tenía 241 caracteres.
- Lanzador desde la carpeta extraída: **7 de 7** comprobaciones aprobadas.
  La copia extraída inició en otro puerto y conservó abierta la instancia
  de la carpeta original.
- La prueba integral se repitió sobre la copia extraída: catálogos,
  11 categorías, recursos servidos por HTTP, entradas Word/PDF y sus
  exportaciones aprobados.

El tamaño y SHA-256 definitivos se registran junto al ZIP, fuera de su
contenido. La publicación en GitHub no forma parte de esta entrega local.

## Límites

La detección es heurística y requiere revisar el resultado. No hay OCR.
La extracción de Word cubre párrafos, tablas, encabezados y pies; el contenido
en imágenes, cuadros de texto, notas y revisiones pendientes requiere
comprobación externa. Las exportaciones reconstruyen el texto y el CSV
conserva los valores originales.

La compilación no tiene firma digital. Las pruebas funcionales no demuestran
compatibilidad con todas las políticas de seguridad de Windows 11 ni
sustituyen una validación en un equipo con Control Inteligente de Aplicaciones
activo. macOS requiere su propia compilación y pruebas.
