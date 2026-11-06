# Verificación de 3.4.3

> Registro histórico de la primera entrega local 3.4.3, anterior a las
> correcciones EGM. La descarga vigente está en el [README](../README.md) y
> la validación posterior en [el cierre EGM](revision-egm/correcciones_pendientes.md).

Entrega local para Windows x64, 6 de noviembre de 2026.

## Alcance

Los separadores abreviados de carátula delimitan las partes y la materia.
Una parte completa puede contener nombres en minúsculas que no figuren en
el catálogo. La limpieza y la validación utilizan esos límites exactos;
la mera cercanía a una palabra como «sobre» no habilita texto arbitrario
como nombre de persona.

Empresas y organismos mantienen su categoría cuando ocupan una parte.
Los encabezados nominales de documentos y trámites se excluyen de las
personas; la capitalización y las partículas no recortan un nombre válido.

Las comprobaciones usan documentos ficticios. Las frases aportadas por la
usuaria se contrastan localmente y no se incorporan a los artefactos.

## Resultados

- Suite Python con el paquete compilado disponible: 931 pruebas y 765
  subpruebas aprobadas. Se omite una prueba de enlaces simbólicos por los
  permisos de Windows y se registra una advertencia de Starlette.
- Frontend: 33 pruebas aprobadas. Auditoría: 173 archivos, 119 módulos
  Python, 4 JSON y 36 enlaces internos, sin errores.
- Carátulas: 20 casos y 207 controles sobre el ejecutable. Se verifican
  nombres desconocidos, minúsculas, capitalización mixta, partículas,
  apellido antes del nombre, saltos de línea, empresas y prosa administrativa.
  Los casos positivos se comprueban en vista previa, Word y PDF.
- Flujo completo de identidades: 24 controles por entrada Word/PDF,
  incluida la coherencia de las variantes en grupos y exportaciones CSV.
- Las seis variantes de la frase aportada pasan 24 controles locales en
  el ejecutable: nombres completos separados y coherencia de la vista previa,
  Word y PDF. El registro conserva únicamente resultados booleanos.
- Arranque: 7 controles aprobados. Categorías: 18. Agrupación: 23 por cada
  modo PERSONA/ALL. Partes de documentos y revisión: 18. Cancelación: 2.
  También pasan las comprobaciones integrales de datos sensibles,
  exportaciones y corrección/unión de grupos.
- Navegador real con Playwright y perfil separado: 18 controles aprobados
  sobre tres carátulas ficticias. Se comprueban detecciones independientes,
  editor, asunto y descargas Word/PDF, sin errores de JavaScript.
  Se inspeccionan las capturas de detecciones y un PDF renderizado.
- Los recursos de interfaz y catálogos coinciden con la fuente. Las tres
  instalaciones anteriores se conservan intactas.

Las evidencias de interfaz se conservan en `build/validation/ui343`.
El registro de integridad y arranque del ZIP final se guarda junto al
paquete en `dist/VERIFICACION_ENTREGA_3.4.3.txt`.

## Límites

La detección requiere revisión. Una variante compatible con varias personas
no se asigna automáticamente a una identidad. No hay OCR ni conservación de
la distribución original; las exportaciones respetan el texto y el formato
del editor. Las sesiones de versiones anteriores no migran a la nueva.
