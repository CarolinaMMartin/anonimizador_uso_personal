# Cambios — Anonimizador Judicial

## 3.3.12 — 18 de septiembre de 2026

- Detección de nombres y apellidos con cualquier capitalización y tildes, basada en los catálogos locales y contexto de personas. Los límites evitan absorber oraciones completas.
- Empresas y organismos con límites propios; protección de vehículos, códigos y otras entidades frente a detecciones de personas.
- Agrupación de variantes en el documento completo: orden invertido, iniciales, nombres parciales y apellidos compuestos. Las coincidencias ambiguas permanecen separadas.
- Detección de apellidos ausentes del catálogo mediante nombres completos encontrados en el documento, conservando evidencia y procedencia.
- Identificadores y etiquetas estables; confirmación, separación y rechazo de agrupaciones coherentes con la exportación.
- Correcciones de guardado, cambio de sesión y exportación en la interfaz.
- NLP sobre todo el texto mediante fragmentos superpuestos: se elimina el corte silencioso a 500.000 caracteres.
- Cancelación atendida durante el análisis; ejecución del análisis en el pool de trabajo.
- Extracción de párrafos, tablas, tablas anidadas, encabezados y pies de Word.
- Carga limitada a 40 MB y rechazo explícito de formatos no admitidos.
- Protección del CSV frente a fórmulas precedidas por espacios.
- Inicio de Windows con puerto disponible y reutilización de la misma copia, conservando otros procesos.
- Manuales y avisos de terceros actualizados; ZIP versionado con SHA-256, exclusión de datos de usuarios e inventario de licencias.

La entrega de esta versión corresponde a Windows x64. macOS requiere su propia compilación y validación. La función de personas conocidas queda pendiente para otra versión.

## Versiones anteriores

El historial de versiones públicas anteriores se conserva en [GitHub Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases). Las revisiones locales intermedias de 3.3.11 se consolidan en 3.3.12.
