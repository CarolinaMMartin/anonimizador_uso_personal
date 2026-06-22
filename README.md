# Anonimizador Judicial

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Windows 10/11 x64](https://img.shields.io/badge/Windows-10%2F11%20x64-blue.svg)](#descargar-para-windows)
[![Procesamiento 100% local](https://img.shields.io/badge/procesamiento-100%25%20local-success.svg)](#privacidad)

Aplicación para anonimizar documentos judiciales argentinos (PDF / DOCX)
con **procesamiento 100 % local**: detección por capas (regex + Presidio
+ spaCy), revisión humana y exportación a Word, PDF y CSV. No envía nada
a servidores externos.

---

## Descargar para Windows

Versión portable para **Windows 10 y 11 de 64 bits**.

No requiere instalar Python ni usar una terminal.

1. Descargá el ZIP portable desde **[GitHub Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest)**.
2. Clic derecho en el ZIP → **Extraer todo**.
3. Abrí la carpeta extraída.
4. Doble clic en **`INICIAR.bat`**.

Se abre solo en el navegador, en <http://127.0.0.1:8787>.

> **No uses "Code → Download ZIP" para instalar la aplicación.** Esa
> opción descarga el código fuente. Para usar el anonimizador, descargá
> el ZIP portable desde **Releases**.

Guía detallada: [docs/MANUAL_INSTALACION.md](docs/MANUAL_INSTALACION.md).
Cómo usar la herramienta: [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md).

---

## Uso en tres pasos

1. **Cargá** un documento Word (`.docx`) o PDF con texto seleccionable.
2. **Analizá y revisá** las detecciones: podés activarlas, editarlas,
   agrupar variantes o agregar datos a mano.
3. **Exportá** el documento anonimizado a Word, PDF o la tabla CSV.

---

## Requisitos

- Windows 10 u 11, 64 bits.
- Un navegador actual (Edge, Chrome o Firefox).
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

- El procesamiento ocurre **íntegramente en tu PC** (`127.0.0.1`).
- No hay llamadas a servicios en la nube, ni seguimiento de uso.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.

---

## Limitaciones

- Solo procesa PDF **digital** (con texto seleccionable) o Word; no lee
  PDF escaneados (imágenes).
- La detección automática **no es perfecta**: revisá siempre antes de
  exportar y no compartas un documento sin verificar que no queden datos
  sensibles.
- La versión publicada para usuarios es **Windows 10/11 de 64 bits**.

---

## Documentación para desarrolladores

Requisitos: **Python 3.10+**. Windows recomendado si vas a generar el
paquete portable; macOS / Linux sirven para desarrollo y tests.

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

Para reportar un bug usá la plantilla en *Issues → New issue*. **No
incluyas datos personales reales** ni en issues ni en tests. Para temas
de seguridad, ver [SECURITY.md](SECURITY.md).

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
