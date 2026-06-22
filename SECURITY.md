# Política de seguridad

## Reportar una vulnerabilidad

Si encontraste un problema de seguridad en el Anonimizador Judicial, te
pedimos que **no abras un issue público**. Mandanos un correo al equipo
de IALAB con los detalles a:

**ialab@derecho.uba.ar**

Incluí, en la medida de lo posible:

- Descripción clara del problema y su impacto potencial.
- Pasos para reproducirlo (input mínimo, versión de la app, sistema
  operativo).
- Si tenés un *proof of concept*, adjuntá el texto / archivo de prueba
  con datos ficticios. **No envíes documentos judiciales reales ni
  datos personales** — usá ejemplos sintéticos.
- Tu nombre / handle para agradecerte públicamente al publicar el fix
  (opcional).

Respondemos en un plazo de **5 días hábiles** con una primera
evaluación. Si confirmamos la vulnerabilidad coordinaremos con vos una
fecha de divulgación responsable, normalmente después de que se
publique el parche.

## Alcance

La aplicación está pensada para correr **100 % local** en
`127.0.0.1:8787`. Las áreas de interés para reportes son:

- **Path traversal / lectura de archivos** vía cualquier endpoint de
  `app/api/`.
- **Inyección** en exports (DOCX, PDF, CSV, Markdown).
- **Procesamiento de PDF/DOCX malicioso** que termine ejecutando código
  o bloqueando el proceso indefinidamente.
- **Persistencia de PII** en `data/sessions.db` que no debiera quedar
  guardada después de cerrar la sesión.
- **Fugas hacia la red.** El binario portable está pensado para
  funcionar sin Internet (`tldextract` offline, sin CDN, sin telemetría).
  Si descubrís llamadas remotas inesperadas, reportalas.

Fuera de alcance: ataques que requieran acceso físico al equipo donde
corre la app, o vulnerabilidades en dependencias upstream que ya estén
parcheadas en la rama estable.

## Versiones soportadas

Solo aplicamos parches de seguridad a la versión publicada más reciente
(`app_version` en `/health`). Si usás un binario portable más antiguo,
te recomendamos actualizar antes de reportar.

## Confidencialidad

Tratamos los reportes con confidencialidad hasta que haya un parche
publicado. Si necesitás compartir información sensible adicional,
indicalo en el primer mensaje y te respondemos con un canal cifrado.
