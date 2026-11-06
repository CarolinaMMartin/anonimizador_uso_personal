# Verificación de 3.4.2

> Registro histórico de esa entrega. Para instalar la versión vigente,
> consultar el [README](../README.md); estos resultados no validan otra versión.

Entrega local para Windows x64, 6 de noviembre de 2026.

## Alcance

La detección combina reglas, catálogos y NLP local de spaCy/Presidio. La
resolución de personas utiliza formas normalizadas, orden de nombre/apellido,
iniciales y unicidad de las variantes dentro del documento. NetworkX reúne
las relaciones admitidas; RapidFuzz se usa para otras categorías.

La revisión corrige dos problemas relacionados: las detecciones que cruzaban
separadores de carátula podían unir personas distintas, y las modificaciones
manuales dejaban sugerencias desactualizadas. Se verifica además la separación
de enumeraciones frente a apellidos compuestos con conjunciones.

El ejemplo aportado se inspecciona localmente. Sus datos no se incorporan a
pruebas, capturas, registros de entrega ni archivos del paquete. Las regresiones
publicables usan documentos ficticios.

## Resultados

- Suite Python sobre el paquete compilado: 812 pruebas y 765 subpruebas
  aprobadas. Una prueba de enlaces simbólicos se omite por los permisos de
  Windows; se registra una advertencia de Starlette.
- Frontend: 33 pruebas aprobadas, incluidas cancelación, fallas de guardado
  y respuestas de una sesión anterior.
- Auditoría: 172 archivos, 119 módulos Python, 4 JSON y 36 enlaces internos;
  sin errores.
- Caso aportado: tres identidades con 5, 6 y 4 menciones. Ninguna variante
  de persona queda sin grupo. Se comprueba la correspondencia en Word, PDF
  y CSV, y se conserva la separación entre partes y materia de la carátula.
- Regresión ficticia completa: 24 controles por entrada Word/PDF; incluye
  detección, sugerencias, confirmación, vista previa y las tres exportaciones.
- Ejecutable: arranque, categorías, agrupación, revisión manual, partes de
  Word, datos sensibles y cancelación aprobados. Las instalaciones anteriores
  se conservan intactas.
- Navegador real con Playwright y perfil separado: 17 controles aprobados
  sobre el ejecutable. Se comprueban grupos, exportaciones, actualización
  tras agregar una variante, cancelación e incorporación explícita a un
  confirmado. Sin errores de JavaScript.
- Capturas inspeccionadas en escritorio (1440 × 1000) y móvil (390 × 844):
  grupos, propuesta de incorporación y editor, sin desbordamiento de la página.
  El PDF descargado desde la interfaz se renderiza y se inspecciona.

Las evidencias de interfaz son ficticias y se conservan en
`build/validation/ui342`. El registro de integridad y arranque del ZIP final
se guarda junto al paquete en `dist/VERIFICACION_ENTREGA_3.4.2.txt`.

## Límites

Una variante compatible con varias personas permanece sin asociación
automática. La persona revisora decide si corresponde unirla. Las confirmaciones
y separaciones manuales no se sustituyen silenciosamente por una nueva propuesta.

No hay OCR ni reconstrucción de la distribución original del documento. Se
conservan el formato elegido y los saltos del editor al exportar. Las sesiones
anteriores permanecen en su aplicación y no migran a la versión nueva.
