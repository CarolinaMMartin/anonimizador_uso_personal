# Guía de despliegue empaquetado (ZIP portable)

Esta guía describe cómo construir y entregar el Anonimizador Judicial
como una **aplicación portable**, lista para usuarios que no quieren o no
pueden instalar Python, pip, spaCy ni otras dependencias.

Hay descargas publicadas para:

- **Windows 10/11 de 64 bits**.
- **macOS**.

La versión vigente se obtiene de `APP_VERSION` en `app/config.py`, se
muestra en la interfaz y también puede consultarse en
<http://127.0.0.1:8787/health> mediante `app_version`.

Para el flujo completo de publicación, ver
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

---

## 1. Qué recibe el usuario final

El usuario descarga desde GitHub Releases el archivo correspondiente a su
sistema:

| Plataforma | Archivo publicado | Inicio |
|------------|-------------------|--------|
| Windows | `AnonimizadorJudicial-Windows.zip` | `INICIAR.bat` |
| macOS | `AnonimizadorJudicial-Mac` | `INICIAR.command` |

El paquete descomprimido contiene el programa, el frontend, el modelo
spaCy, los manuales y los avisos de licencias. No requiere instalar nada
adicional.

Contenido principal:

| Elemento | Función |
|----------|---------|
| `INICIAR.bat` / `INICIAR.command` | Inicia la aplicación |
| `VERIFICAR.bat` / `VERIFICAR.command` | Abre la verificación local |
| `AnonimizadorJudicial-NLP.exe` o `AnonimizadorJudicial-NLP.app` | Aplicación empaquetada |
| `_internal/` o contenido interno de la `.app` | Librerías embebidas |
| `models/es_core_news_md/` | Modelo spaCy + licencia GPL-3.0 |
| `LICENSE` | Apache 2.0 del código de la aplicación |
| `NOTICE` | Copyright y nota de marca |
| `THIRD_PARTY_NOTICES.txt` | Inventario de licencias |
| `LICENSES/` | Textos completos de licencias de terceros |
| `LEEME_INSTALACION.txt` | Inicio rápido |
| `MANUAL_INSTALACION.md` | Instalación y problemas frecuentes |
| `MANUAL_USUARIO.md` | Cómo usar la herramienta |

---

## 2. Instalación del usuario

### Windows

1. Descomprimir el ZIP completo.
2. Ejecutar `INICIAR.bat`.
3. Abrir <http://127.0.0.1:8787> si el navegador no se abre solo.

### macOS

1. Descomprimir el archivo completo.
2. La primera vez, hacer clic derecho en `INICIAR.command` → **Abrir**.
3. Abrir <http://127.0.0.1:8787> si el navegador no se abre solo.

No hay pasos de consola ni instalación de dependencias para el usuario
final.

---

## 3. Verificación posterior al empaquetado

En cada plataforma:

1. Abrir <http://127.0.0.1:8787/health>.
2. Confirmar:
   - `app_version` coincide con la Release.
   - `presidio.available`: `true`.
   - `spacy.available`: `true`.
3. Probar sin conexión a Internet.
4. Cargar un documento ficticio.
5. Analizar, revisar y exportar a Word o PDF.
6. Confirmar la presencia de:
   - `THIRD_PARTY_NOTICES.txt`.
   - licencia del modelo `es_core_news_md`.
   - `NOTICE`.

Checklist completo de cumplimiento: [COMPLIANCE.md](COMPLIANCE.md).

---

## 4. Generación del paquete — desarrollo

Estos comandos son para quienes mantienen o reutilizan el proyecto, no
para usuarios finales.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\build_portable_full.py
.venv\Scripts\python scripts\package_release.py --suffix v3.3.10-Windows-x64
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python scripts/install_nlp.py
python scripts/build_portable_full.py
python scripts/package_release.py --suffix v3.3.10-macOS
```

El paquete generado queda en `dist/`. PyInstaller debe ejecutarse en el
mismo sistema operativo para el que se genera el portable.

---

## 5. Personalización y reutilización

Antes de redistribuir una versión derivada conviene revisar:

- **Logo y marca:** el logo IALAB está en `frontend/logo-ialab.svg/.png`.
  Quien no tenga autorización institucional debe reemplazarlo, conforme a
  [NOTICE](../NOTICE).
- **Canal de soporte:** adaptar los manuales a la persona u organización
  que mantendrá el fork.
- **Diccionarios locales:** pueden agregarse recursos propios en
  `data/dictionaries/`.
- **Regex específicos:** `regex_limpio_v2.json` puede extenderse sin
  modificar el motor principal.
- **Licencias:** conservar `LICENSE`, `NOTICE`,
  `THIRD_PARTY_NOTICES.txt`, `LICENSES/` y la licencia del modelo spaCy.

---

## 6. Distribución y actualización

- Publicar los paquetes como archivos adjuntos de una GitHub Release, no
  dentro del historial Git.
- Indicar en cada Release la versión, plataforma, tamaño y SHA-256.
- Mantener los nombres usados por los enlaces directos del README:
  `AnonimizadorJudicial-Windows.zip` y `AnonimizadorJudicial-Mac`.
- Para actualizar, el usuario descarga la versión nueva, la extrae en otra
  carpeta y abre esa copia.
- Ver [SECURITY.md](../SECURITY.md) para reportes de vulnerabilidades y
  [MANUAL_INSTALACION.md](MANUAL_INSTALACION.md) para soporte básico.
