# Anonimizador Judicial

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Última versión](https://img.shields.io/github/v/release/CarolinaMMartin/anonimizador_uso_personal?label=%C3%BAltima%20versi%C3%B3n)](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest)
[![Windows y macOS](https://img.shields.io/badge/Windows%20%7C%20macOS-disponible-blue.svg)](#descargar-la-aplicación)
[![Procesamiento 100% local](https://img.shields.io/badge/procesamiento-100%25%20local-success.svg)](#privacidad)

Aplicación para anonimizar documentos judiciales argentinos (PDF / DOCX)
con **procesamiento 100 % local**: detección por capas (regex + Presidio
+ spaCy), revisión humana y exportación a Word, PDF y CSV. No envía nada
a servidores externos.

---

## Descargar la aplicación

Elegí la versión correspondiente a tu equipo.

### Windows 10/11 — 64 bits

[➜ Descargar ZIP para Windows](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest/download/AnonimizadorJudicial-Windows.zip)

Después de descargar:

1. Clic derecho en el ZIP → **Extraer todo**.
2. Abrí la carpeta extraída.
3. Doble clic en **`INICIAR.bat`**.


### macOS

[➜ Descargar ZIP para Mac](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest/download/AnonimizadorJudicial-Mac)

Después de descargar:

1. Descomprimí el archivo.
2. Abrí la carpeta extraída.
3. La primera vez, hacé clic derecho en **`INICIAR.command`** → **Abrir**.

La aplicación se abre en el navegador, en <http://127.0.0.1:8787>.
No requiere instalar Python ni usar una terminal.

### Cómo saber si tenés la última versión

La versión instalada aparece en la parte superior de la aplicación, junto
al indicador **“100% local”**. Comparala con la insignia **“última
versión”** que aparece al comienzo de este README o con la versión indicada
en [Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest).
Si coinciden, ya tenés la versión más reciente.

> **No uses "Code → Download ZIP" (el botón verde de arriba).** Eso
> descarga el código fuente, no la aplicación. Usá únicamente los enlaces
> de descarga de esta sección.

- Notas de versión y verificación SHA-256: <https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest>
- Guía de instalación: [docs/MANUAL_INSTALACION.md](docs/MANUAL_INSTALACION.md).
- Cómo usar la herramienta:[Manual de usuario](https://docs.google.com/document/d/1t6b5YhVHeYPvF67g9FQiOhXRq0xYIf17I-bfhhik9no/edit?tab=t.0)

---

## Uso en tres pasos

1. **Cargá** un documento Word (`.docx`) o PDF con texto seleccionable.
2. **Analizá y revisá** las detecciones: podés activarlas, editarlas,
   agrupar variantes o agregar datos a mano.
3. **Exportá** el documento anonimizado a Word, PDF o la tabla CSV.

---

## Requisitos

- Windows 10/11 de 64 bits o macOS.
- Un navegador actual (Edge, Chrome, Firefox o Safari).
- No requiere Python, Internet ni permisos de administrador.

---

## Funcionalidades

- Carga de `.docx` o PDF digital (texto seleccionable).
- Detección automática de personas, DNI, CUIT/CUIL, empresas, emails,
  teléfonos, domicilios, patentes, expedientes y organismos.
- Tres modos de etiquetado: categorizado (`[PERSONA_1]`), genérico
  (`[NOMBRE]`) o iniciales (`J.P.G.`).
- Revisión humana: cambiar tipo, editar la sustitución, unir variantes
  similares y agregar detecciones manualmente.
- Editor final para retocar texto y formato antes de exportar.
- Exportación a Word, PDF, CSV de equivalencias y Markdown.

---

## Privacidad

- El procesamiento ocurre **íntegramente en tu equipo** (`127.0.0.1`).
- No hay llamadas a servicios en la nube, ni seguimiento de uso.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.

---

## Limitaciones

- Solo procesa PDF **digital** (con texto seleccionable) o Word; no lee
  PDF escaneados (imágenes). Para poder incorporar esta funcionalidad, se puede aregar un OCR. Se eligió matener esta opcion liviana. 
- La detección automática **no es perfecta**: revisá siempre antes de
  exportar y no compartas un documento sin verificar que no queden datos
  sensibles.
- Las versiones publicadas para usuarios están disponibles para Windows
  y macOS.

---

## Documentación para desarrolladores

Requisitos: **Python 3.11+** (las dependencias fijadas del build
verificado requieren 3.11 o superior). Windows recomendado si vas a
generar el paquete portable; macOS / Linux sirven para desarrollo y tests.

```powershell
git clone https://github.com/CarolinaMMartin/anonimizador_uso_personal.git
cd anonimizador_uso_personal
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\run_dev.py
```

Abrí <http://127.0.0.1:8787>. Verificá las capas NLP en
<http://127.0.0.1:8787/health>: `presidio` y `spacy` deben aparecer en
`true`.

En Windows podés usar el lanzador de desarrollo `INICIAR_DESARROLLO.bat`
(macOS / Linux: `INICIAR_DESARROLLO.sh`). El nombre `INICIAR.bat` queda
reservado para el paquete portable.

Para correr los tests:

```powershell
.venv\Scripts\python -m pytest tests/ -v
```

Generar y publicar el paquete portable: ver
[docs/DEPLOY.md](docs/DEPLOY.md) y
[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

### Arquitectura

- **FastAPI** en `127.0.0.1:8787` (solo localhost).
- **Frontend** HTML / CSS / JS sin CDN (fuentes del sistema).
- **Detección por capas:** regex argentinos, Microsoft Presidio + spaCy
  (`es_core_news_md`) y un catálogo externo `regex_limpio_v2.json`.
- **PDF:** pdfplumber (lectura) + ReportLab (export).
- **Resolución:** RapidFuzz + grafo (NetworkX) + panel de revisión.

---

## Contribuciones

Antes de mandar un PR leé:

- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, tests, estilo y áreas
  donde necesitamos ayuda.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Licencia

- **Código de la aplicación:** Apache 2.0 (ver [LICENSE](LICENSE)).
- **Componentes de terceros:** [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)
  y [LICENSES/](LICENSES/).
- **Modelo spaCy `es_core_news_md`:** GPL-3.0; se incluye solo en el
  paquete portable, no en el código fuente.
- **Logo y nombre IALAB:** marcas institucionales, **no cubiertas** por
  la licencia Apache 2.0 (ver [NOTICE](NOTICE)).

---

Desarrollado por **IALAB** — Laboratorio de Innovación e Inteligencia
Artificial, Facultad de Derecho, Universidad de Buenos Aires.
