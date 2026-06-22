## Resumen

<!-- Descripción corta del cambio y el problema que resuelve. -->

## Issue relacionado

<!-- Closes #N (o "Sin issue, cambio menor"). -->

## Tipo de cambio

- [ ] Bug fix (corrección que no rompe API)
- [ ] Feature nueva (cambio no disruptivo)
- [ ] Cambio que rompe compatibilidad
- [ ] Refactor / limpieza
- [ ] Documentación / docs

## Verificación

- [ ] `pytest tests/` corre sin fallas en local.
- [ ] Agregué tests para el cambio (o expliqué por qué no hace falta).
- [ ] Probé manualmente el flujo afectado (cargar → analizar → revisar
      → exportar) si toqué detección o UI.
- [ ] No introduje dependencias nuevas, o actualicé `requirements.txt`,
      `THIRD_PARTY_NOTICES.txt` y `NOTICE` si correspondía.
- [ ] No agregué datos personales reales en código, tests, fixtures ni
      mensajes de commit.
- [ ] La feature sigue corriendo 100 % local (sin llamadas a red).

## Notas para revisores

<!-- Cualquier contexto que ayude a entender el diff (decisiones de
diseño, trade-offs, áreas frágiles). -->
