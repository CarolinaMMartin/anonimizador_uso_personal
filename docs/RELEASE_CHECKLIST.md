# Publicación de versiones

Repositorio: [anonimizador_uso_personal](https://github.com/CarolinaMMartin/anonimizador_uso_personal).
La versión 3.3.13 se entrega para Windows x64. Publicar macOS únicamente después de construir y verificar esa misma versión en una Mac.

1. Actualizar `APP_VERSION`, README, manuales, changelog y notas de versión. Las propuestas pendientes no deben aparecer como funcionalidades disponibles.
2. Revisar todos los archivos publicables y ejecutar `python scripts/audit_repository.py`, `python -m pip check`, `python -m pytest tests -q` y `node --test tests/frontend_session.test.cjs`.
3. Construir en el sistema de destino con `python scripts/build_portable_full.py`. Repetir pytest con el paquete presente; no debe omitir pruebas de estructura.
4. Ejecutar `python scripts/portable_smoke.py` y `python scripts/check_grouping.py --url http://127.0.0.1:PUERTO --learned-alias-cases` sobre el ejecutable compilado. Los casos deben ser ficticios.
5. Crear la entrega con `python scripts/package_release.py --output dist/AnonimizadorJudicial-Windows.zip`. Verificar el CRC, SHA-256 y exclusión de sesiones, documentos, equivalencias, registros y credenciales.
6. Extraer el ZIP en una carpeta nueva y verificar inicio, versión, capas NLP locales, carga y exportaciones. El lanzador debe conservar procesos anteriores.
7. Guardar el código revisado en Git. Crear el tag `vVERSION` sobre el mismo commit que se compila y una Release con notas, plataforma, limitaciones, ZIP y SHA-256.
8. Comprobar los enlaces de descarga y la coincidencia entre versión del tag, código, interfaz, `/health` y `VERSION_APP.txt`.

## Automatización de Windows

[release-windows.yml](../.github/workflows/release-windows.yml) construye y verifica el portable antes de generar un artifact. Una ejecución manual publica solamente si se selecciona `publish`. Un commit en `main` con el marcador explícito `[publicar-version]` también solicita la publicación de la versión definida en el código.

Las ejecuciones por tag y las ejecuciones manuales sin `publish` construyen artifacts para revisión. Los demás commits en `main` no publican. La publicación crea una Release nueva y adjunta el ZIP y su SHA-256 después de pasar las verificaciones; no reemplaza archivos de versiones anteriores.

Las notas se obtienen de [NOTAS_VERSION.md](NOTAS_VERSION.md). Si falla una comprobación, corregir el problema y repetir la validación antes de publicar. No usar documentos reales en Issues, tests, capturas ni artifacts.
