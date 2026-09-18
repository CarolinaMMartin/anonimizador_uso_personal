# Personas conocidas: propuesta de funcionalidad

Propuesta revisada contra el motor local 3.3.12. Todavía no está
implementada en la interfaz ni en el ejecutable.

## Objetivo

Permitir que el usuario declare una persona y encuentre sus posibles menciones
sin tener que escribir todas las variantes. La persona declarada debe servir
como referencia aunque su nombre completo nunca aparezca en el documento.
La búsqueda se realiza localmente sobre el texto original.

## Flujo propuesto

Agregar un panel **Personas conocidas** en la revisión del documento, junto a
las identidades. El usuario puede ingresar una o varias personas.

1. Escribir un nombre completo, por ejemplo `María Pérez`.
2. El panel muestra la interpretación: **Nombre(s): María / Apellido(s): Pérez**.
   Para nombres compuestos, esta separación es editable: no se exige que las
   palabras estén en el catálogo para aceptar la persona.
3. Pulsar **Buscar variantes**. La búsqueda todavía no cambia el documento.
4. Ver cada forma encontrada, cantidad, contexto y posibles personas compatibles.
   Se puede expandir una forma para revisar sus ocurrencias individualmente.
5. Revisar las coincidencias directas y elegir las referencias abreviadas.
   Las ambiguas quedan sin seleccionar hasta que el usuario las asigne.
6. Pulsar **Anonimizar seleccionadas**. Las menciones asignadas a esa persona
   comparten la sustitución, por ejemplo `[PERSONA_1]` en modo categorizado.

La lista se conserva durante la sesión del documento y se limpia al cambiar de
documento. Se pueden agregar referencias después del análisis sin borrar las
correcciones manuales anteriores. Su incorporación a la configuración previa al
análisis puede hacerse después; el primer alcance es el panel de revisión.

## Reglas generales de coincidencia

| Texto encontrado | Tratamiento propuesto |
|---|---|
| `María Pérez`, `MARIA PEREZ` | Coincidencia directa del nombre declarado. |
| `Pérez, María` | Coincidencia directa usando la separación de nombres y apellidos confirmada por el usuario. |
| `M. Pérez`, `M.Perez` | Variante abreviada; mostrar contexto y personas compatibles. |
| `Pérez` | Referencia corta; mostrar contexto y posibles identidades. |
| `M. P.` o `María` aislados | Excluidos de la búsqueda inicial para reducir ruido. |
| `Marta Pérez` | Otra persona; no tomar su apellido como una mención de María. |
| `Pérez SA`, una dirección o `Perez123` | Excluir las coincidencias dentro de entidades protegidas y códigos. |

No se fija una lista de variantes por cada ejemplo. Las formas se construyen
desde los nombres y apellidos declarados: omisiones acotadas, iniciales de
nombres de pila, ambos órdenes con coma, tildes, mayúsculas, guiones,
apóstrofos, partículas y saltos de línea. Se mantienen los límites de palabra
y las posiciones del texto original. Los conectores necesitan evidencia del
nombre declarado; no se incorpora una frase alrededor de una coincidencia.

Las coincidencias directas pueden aparecer preseleccionadas si no tienen
conflictos. Las abreviadas requieren revisión. En particular, si el documento
contiene María Pérez y Marta Pérez, `M. Pérez` es compatible con ambas.
También se consideran las personas detectadas que el usuario no ingresó.
Que haya una sola candidata encontrada no demuestra por sí solo la identidad.

El contexto sirve para que el usuario decida; en esta primera versión no se
promete inferir automáticamente qué persona habló en cada párrafo. No se unen
identidades por similitud de escritura ni se generan apodos o errores de tipeo.

## Cambios necesarios en el motor

- Guardar las personas declaradas con identificador estable y nombres/apellidos
  separados. Son referencias; no son detecciones con posiciones inventadas.
- Reutilizar el reconocimiento acotado de `document_aliases.py`, adaptando la
  política de variantes a referencias explícitas. La coma se puede generar por
  la estructura confirmada del nombre. Debe contemplarse la escritura en
  minúsculas sin convertir palabras comunes aisladas en asignaciones directas.
- Buscar coincidencias y resolver sus candidatas en el servidor. Proteger los
  nombres completos de otras personas y las entidades no personales. La
  revisión de candidatos usa todas las personas disponibles, aunque el usuario
  solo quiera anonimizar una.
- Separar la búsqueda de su aplicación. El resultado incluye rangos, contexto,
  forma encontrada, candidatas y motivo de ambigüedad. La aplicación vuelve a
  validar las selecciones contra el documento y el estado vigente.
- Permitir asignaciones **por ocurrencia**. La agrupación actual por texto
  normalizado no alcanza si distintas apariciones de `Pérez` pertenecen a
  personas diferentes. Separar esas posiciones sin duplicar reemplazos ni
  cambiar las ocurrencias que el usuario no seleccionó.
- Aplicar una sustitución coherente con el modo elegido, integrar grupos y
  detecciones ya existentes, y mantener las decisiones en Word, PDF y CSV.
  El CSV registra las menciones realmente encontradas; la persona declarada
  puede aparecer como identidad asociada, sin inventar ocurrencias de su nombre.
- Conservar desactivaciones, ediciones y rechazos anteriores; evitar
  duplicados al repetir la búsqueda. Invalidar resultados pendientes si cambia
  el documento y no anunciar éxito antes de que el servidor aplique el cambio.

## Viabilidad comprobada y verificación pendiente

Se probó el buscador actual con una referencia ficticia `Maria Perez` sobre
texto en memoria. Encontró el nombre completo, iniciales con y sin espacio y
el apellido solo. Encontró abreviaturas incluso sin aparición del nombre
completo. No se modificó ninguna sesión abierta.

La misma prueba identificó dos ajustes necesarios: la referencia natural
actual no reconoce como una única mención el orden inverso con coma, y el
buscador de alias aislado puede encontrar el apellido dentro del nombre
completo de otra persona. Por eso no basta con conectar un campo al buscador.

Para implementar, verificar nombres ajenos al catálogo, compuestos y Unicode;
iniciales sin nombre completo en el texto; varias personas con apellido o
inicial compartidos; asignaciones diferentes de una misma forma; coincidencias
ya existentes o desactivadas; frases, empresas, domicilios y códigos; búsquedas
repetidas, cambio de documento y exportaciones coherentes de Word/PDF/CSV.
