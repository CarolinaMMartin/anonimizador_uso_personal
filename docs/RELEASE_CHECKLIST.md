# Checklist de publicación (GitHub Releases)

Los paquetes portables **no se versionan dentro del historial Git**. Se
publican como archivos adjuntos de una **GitHub Release**.

Plataformas publicadas:

| Plataforma | Archivo estable usado por el README | Inicio |
|------------|--------------------------------------|--------|
| Windows 10/11 x64 | `AnonimizadorJudicial-Windows.zip` | `INICIAR.bat` |
| macOS | `AnonimizadorJudicial-Mac` | `INICIAR.command` |

Repositorio: <https://github.com/CarolinaMMartin/anonimizador_uso_personal>

---

## Checklist por versión

1. **Actualizar `APP_VERSION`** en [`app/config.py`](../app/config.py).
   Esa versión aparece en la interfaz, en `/health` y en FastAPI.

2. **Ejecutar los tests.**

   ```bash
   python -m pytest tests/ -v
   ```

3. **Generar cada portable en su sistema operativo.**

   PyInstaller no genera de forma cruzada: el paquete Windows se construye
   en Windows y el de macOS en una Mac.

   ```bash
   python scripts/install_nlp.py
   python scripts/build_portable_full.py
   python scripts/test_portable_smoke.py
   python scripts/package_release.py --suffix vVERSION-PLATAFORMA
   ```

4. **Probar la copia que realmente se va a publicar.**

   En una carpeta limpia:

   - extraer el paquete completo;
   - iniciar con `INICIAR.bat` o `INICIAR.command`;
   - abrir `/health`;
   - confirmar que `app_version` coincide con la Release;
   - confirmar `presidio.available` y `spacy.available` en `true`;
   - cargar un documento ficticio;
   - exportar al menos a Word o PDF.

5. **Verificar la estructura del paquete.**

   Debe incluir:

   - aplicación o ejecutable;
   - launcher y verificador de la plataforma;
   - frontend;
   - modelo spaCy y su licencia;
   - manuales;
   - `LICENSE`;
   - `NOTICE`;
   - `THIRD_PARTY_NOTICES.txt`;
   - `LICENSES/`;
   - `COMPLIANCE.md`.

   No debe incluir sesiones, bases de datos, documentos reales, logs,
   credenciales ni archivos `.env`.

6. **Calcular SHA-256** para cada archivo publicado.

   Windows:

   ```powershell
   Get-FileHash .\AnonimizadorJudicial-Windows.zip -Algorithm SHA256
   ```

   macOS:

   ```bash
   shasum -a 256 AnonimizadorJudicial-Mac
   ```

7. **Crear el tag y la Release.**

   ```bash
   git tag vVERSION
   git push origin vVERSION
   ```

   La Release debe indicar:

   - versión;
   - plataformas disponibles;
   - instrucciones de inicio;
   - cambios principales;
   - limitaciones conocidas;
   - SHA-256 de cada descarga.

8. **Subir los dos archivos a la misma Release.**

   Mantener los nombres estables porque el README utiliza enlaces directos:

   ```text
   AnonimizadorJudicial-Windows.zip
   AnonimizadorJudicial-Mac
   ```

9. **Comprobar los enlaces del README.**

   Abrir el repositorio en una ventana privada y verificar que ambos
   botones descarguen el archivo correcto.

10. **Comprobar la versión visible.**

    - La insignia “última versión” del README debe apuntar a la Release
      recién publicada.
    - La interfaz debe mostrar la misma versión junto al indicador
      “100% local”.
    - `/health` debe devolver esa misma versión en `app_version`.

---

## Notas

- No subir ZIP, ejecutables ni bases de datos al historial Git.
- No usar documentos reales en tests, Issues o capturas.
- No prometer plazos de soporte.
- Conservar todos los avisos y textos de licencia al reutilizar o
  redistribuir el proyecto.
- Si un fork no tiene autorización para usar la marca IALAB, debe
  reemplazar logo y referencias institucionales conforme a `NOTICE`.

## Automatización disponible

El workflow
[`.github/workflows/release-windows.yml`](../.github/workflows/release-windows.yml)
construye el portable de Windows, ejecuta tests y genera un artifact con su
SHA-256. No publica automáticamente la Release: la revisión y publicación
siguen siendo manuales.

El paquete de macOS se genera actualmente en una Mac siguiendo esta misma
lista de control.
