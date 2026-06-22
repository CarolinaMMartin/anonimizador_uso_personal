# Checklist de publicación (GitHub Releases)

El paquete portable **no se versiona en Git**. Se publica como asset de
una **GitHub Release**. Esta guía describe el proceso para la versión
**Windows 10/11 de 64 bits**.

Repositorio: <https://github.com/CarolinaMMartin/anonimizador_uso_personal>

---

## Pasos

1. **Actualizar `APP_VERSION`** en [`app/config.py`](../app/config.py).
   Es la fuente única de versión (la usan `/health`, FastAPI y los
   scripts).

2. **Ejecutar los tests.**

   ```powershell
   .venv\Scripts\python -m pytest tests/ -v
   ```

3. **Generar el portable** (en una PC Windows con el modelo instalado).

   ```powershell
   .venv\Scripts\python scripts\install_nlp.py
   .venv\Scripts\python scripts\build_portable_full.py
   ```

4. **Ejecutar los smoke tests.**

   ```powershell
   .venv\Scripts\python scripts\test_portable_smoke.py
   ```

5. **Generar el ZIP final** con sufijo de versión y plataforma.

   ```powershell
   .venv\Scripts\python scripts\package_release.py --suffix v3.3.10-Windows-x64
   ```

   El nombre recomendado del asset es:

   ```text
   AnonimizadorJudicial-vVERSION-Windows-x64.zip
   ```

   Ejemplo: `AnonimizadorJudicial-v3.3.10-Windows-x64.zip`.

   Nota: el nombre **interno** del ejecutable
   (`AnonimizadorJudicial-NLP.exe`) y el nombre base que generan los
   scripts (`AnonimizadorJudicial-NLP-...`) no se cambian para no romper
   los scripts existentes. El nombre recomendado de arriba es el del ZIP
   **público**; si querés ese nombre exacto, renombrá el ZIP final a mano
   antes de subirlo.

6. **Probarlo en una PC Windows limpia** (sin Python instalado): extraer,
   ejecutar `INICIAR.bat`, verificar `/health` y exportar un documento de
   prueba con datos ficticios.

7. **Calcular el SHA-256** del ZIP y guardarlo en un archivo `.sha256`.

   ```powershell
   certutil -hashfile AnonimizadorJudicial-v3.3.10-Windows-x64.zip SHA256 > AnonimizadorJudicial-v3.3.10-Windows-x64.zip.sha256
   ```

8. **Crear el tag** de versión.

   ```powershell
   git tag v3.3.10
   git push origin v3.3.10
   ```

9. **Crear la GitHub Release** asociada al tag (desde la pestaña
   *Releases* o con `gh release create v3.3.10`). Indicar en las notas el
   **tamaño de descarga y descomprimido** medidos en el paso 6.

10. **Subir el ZIP y el archivo SHA-256** como assets de la Release.

11. **Subir también una copia con nombre estable** para que el link
    directo del README siga funcionando sin editarse en cada versión:

    ```powershell
    Copy-Item AnonimizadorJudicial-NLP-v3.3.10-Windows-x64.zip AnonimizadorJudicial-Windows.zip
    Copy-Item AnonimizadorJudicial-NLP-v3.3.10-Windows-x64.zip.sha256 AnonimizadorJudicial-Windows.zip.sha256
    # Reescribir el nombre del archivo dentro del .sha256:
    (Get-Content AnonimizadorJudicial-Windows.zip.sha256) -replace "AnonimizadorJudicial-NLP-v3.3.10-Windows-x64.zip", "AnonimizadorJudicial-Windows.zip" | Set-Content AnonimizadorJudicial-Windows.zip.sha256
    gh release upload v3.3.10 AnonimizadorJudicial-Windows.zip AnonimizadorJudicial-Windows.zip.sha256 --clobber
    ```

    El link del README usa
    `/releases/latest/download/AnonimizadorJudicial-Windows.zip`, por lo
    que mientras subas ese asset con el mismo nombre en cada Release, el
    botón de descarga seguirá apuntando al ZIP correcto.

12. **Comprobar el enlace** desde el README haciendo clic en el botón de
    descarga: debe bajar el ZIP nuevo directamente.

---

## Notas

- No subir binarios, ZIP ni bases de datos al historial de Git.
- No prometer plazos de soporte ni respuesta.
- Mientras no exista un paquete probado para macOS o Linux, publicar
  únicamente la descarga de **Windows x64**.

## Sobre la automatización

Hay un workflow opcional en
[`.github/workflows/release-windows.yml`](../.github/workflows/release-windows.yml)
que construye el portable en un runner `windows-latest`, corre los tests
y los smoke tests, arma el ZIP, calcula el SHA-256 y los sube como
**artifacts** (no publica la Release automáticamente).

Ese workflow es de ejecución manual (`workflow_dispatch`) y todavía
**no fue verificado de punta a punta en GitHub Actions**. El build con
PyInstaller + modelo spaCy es pesado y puede requerir ajustes de tiempo
o de caché. Hasta confirmar una corrida verde:

- Hacé el build de forma **local en Windows** siguiendo los pasos de
  arriba, y
- usá el workflow solo como apoyo, revisando manualmente el artifact
  antes de publicar una Release.
