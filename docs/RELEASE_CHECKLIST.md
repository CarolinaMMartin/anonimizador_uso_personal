# Publicación de versiones

Repositorio: [anonimizador_uso_personal](https://github.com/CarolinaMMartin/anonimizador_uso_personal).
La versión 3.4.4 se entrega para Windows x64. Publicar macOS únicamente después de construir y verificar esa misma versión en una Mac.

El paquete previsto para la primera publicación IALAB usa `AnonimizadorJudicial-3.4.4-Windows.zip`
y su SHA-256, obtenidos de `dist/AnonimizadorJudicial-NLP-3.4.4/`.
Código, interfaz, manuales y paquete deben identificar 3.4.4. Para futuras
entregas, usar una versión nueva.

1. Actualizar `APP_VERSION`, los parámetros de caché del frontend, README, manuales, changelog y notas de versión. Las propuestas pendientes no deben aparecer como funcionalidades disponibles.
2. Revisar todos los archivos publicables. Antes del primer pytest, fijar `$env:ANON_PKG_DIR = 'dist/AnonimizadorJudicial-NLP-3.4.4'` para no evaluar una instalación anterior. Ejecutar `python scripts/audit_repository.py`, `python -m pip check`, `python -m pytest tests -q` y `node --test tests/frontend_session.test.cjs`.
3. Construir en el sistema de destino con Python 3.12–3.13 y `python scripts/build_portable_full.py --output dist/AnonimizadorJudicial-NLP-3.4.4`. Comprobar que `DEPENDENCIAS_BUILD.txt`, `LICENSES/INVENTARIO_BUILD.json` y `BUILD_PROVENANCE.json` procedan de ese build. Copiar el inventario de texto final a `docs/dependencies-frozen.txt`. Repetir pytest con `ANON_PKG_DIR` apuntando a esa carpeta; no debe omitir pruebas de estructura ni evaluar un paquete anterior.
4. Iniciar esa copia mediante `check_windows_launcher.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --keep-running` y tomar su puerto de `PUERTO_ACTUAL.txt`. Ejecutar `portable_smoke.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --port PUERTO --use-existing`, `check_grouping.py --url http://127.0.0.1:PUERTO --learned-alias-cases`, `check_document_parts.py --url http://127.0.0.1:PUERTO`, `check_sensitive_portable.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --port PUERTO` y `check_identity_flow.py --url http://127.0.0.1:PUERTO`, todos bajo `scripts/`. Verificar entradas Word/PDF y leer el texto de ambas exportaciones. Los casos deben ser ficticios.
5. Repetir `python scripts/check_identity_flow.py --caption-cases --url http://127.0.0.1:PUERTO` para las carátulas en minúsculas, apellidos fuera del catálogo, separadores aislados, saltos de línea y prosa. Crear la entrega con `python scripts/package_release.py --package dist/AnonimizadorJudicial-NLP-3.4.4 --output dist/AnonimizadorJudicial-3.4.4-Windows.zip`. Verificar el CRC, SHA-256 y exclusión de sesiones, documentos, equivalencias, registros y credenciales.
6. Extraer el ZIP en una carpeta nueva y verificar inicio, versión, capas NLP locales, carga y exportaciones. El lanzador debe conservar procesos anteriores. Comprobar que la entrega solo incluya los manuales e informe de verificación actuales; conservar los antecedentes en `docs/historico/` y las copias locales anteriores en `_archivo/`.
7. Guardar el código revisado en Git. Crear el tag `vVERSION` sobre el mismo commit que se compila y una Release con notas, plataforma, limitaciones, ZIP y SHA-256.
8. Comprobar los enlaces de descarga y la coincidencia entre versión del tag, código, interfaz, `/health` y `VERSION_APP.txt`. Los enlaces públicos deben apuntar a `CarolinaMMartin/anonimizador_uso_personal`; descargar el adjunto publicado y comparar su SHA-256 con el paquete verificado antes de anunciarlo.

## Automatización de Windows

[release-windows.yml](../.github/workflows/release-windows.yml) construye y verifica el portable antes de generar un artifact. Una ejecución manual publica solamente si se selecciona `publish`. Un commit en `main` con el marcador explícito `[publicar-version]` también solicita la publicación de la versión definida en el código.

Las ejecuciones por tag y las ejecuciones manuales sin `publish` construyen artifacts para revisión. Los demás commits en `main` no publican. La publicación crea una Release nueva y adjunta el ZIP y su SHA-256 después de pasar las verificaciones; no reemplaza archivos de versiones anteriores.

Las notas se obtienen de [NOTAS_VERSION.md](NOTAS_VERSION.md). Si falla una comprobación, corregir el problema y repetir la validación antes de publicar. No usar documentos reales en Issues, tests, capturas ni artifacts.

Volver a empaquetar exige la procedencia registrada del ejecutable. Si el
entorno, los fuentes de compilación o el binario cambiaron, reconstruir en
una carpeta nueva; no reescribir los inventarios para aparentar coincidencia.

El nombre del ZIP se obtiene del enlace Windows del README y debe coincidir
con la versión del código. La auditoría rechaza repositorios, tags o checksums
incoherentes. Al publicar, los enlaces relativos de las notas se convierten
en enlaces al commit de esa entrega.
