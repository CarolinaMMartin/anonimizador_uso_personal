# Anonimizador Judicial

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![Procesamiento 100% local](https://img.shields.io/badge/procesamiento-100%25%20local-success.svg)](#privacidad-y-seguridad)

Aplicación de escritorio de uso personal para anonimizar documentos judiciales argentinos
(PDF / DOCX) con **procesamiento 100 % local**, detección por capas
(regex + Presidio + spaCy), resolución de entidades y revisión humana
asistida.

> Pensada para juzgados, defensorías, fiscalías, estudios jurídicos y
> equipos académicos que necesitan publicar o compartir documentos sin
> exponer datos personales. No envía nada a servidores externos.

---

## Para quien recibe el ZIP (usuarios / Poder Judicial)

**No hay que instalar Python, pip, spaCy ni nada más.**

1. Descomprimí el ZIP completo (ej. `AnonimizadorJudicial-NLP-PJ-v3.3.10.zip`).
2. Doble clic en **`INICIAR.bat`**.
3. Se abre <http://127.0.0.1:8787> en el navegador.

Guías incluidas en el ZIP:

| Archivo | Contenido |
|---------|-----------|
| `LEEME_INSTALACION.txt` | Inicio rápido (3 pasos) |
| `MANUAL_INSTALACION.md` | Instalación y problemas frecuentes |
| `MANUAL_USUARIO.md` | Cómo usar la herramienta |
| `THIRD_PARTY_NOTICES.txt` | Licencias de software incluido |
| `COMPLIANCE.md` | Informe para IT / sistemas |

Verificación: `VERIFICAR.bat` o <http://127.0.0.1:8787/health> →
`presidio` y `spacy` en `true`.

No requiere Internet.

---

## Para desarrolladores

Requisitos: **Python 3.10+**. Windows recomendado si vas a generar el
`.exe` portable; macOS / Linux funcionan para desarrollo y tests.

```powershell
git clone https://github.com/IALAB-UBA/anonimizador-judicial.git
cd anonimizador-judicial
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\run_dev.py
```

Abrí <http://127.0.0.1:8787>. Verificá NLP: <http://127.0.0.1:8787/health>.

Para correr los tests:

```powershell
.venv\Scripts\python -m pytest tests/ -v
```

### Generar el ZIP portable (entrega)

```powershell
.venv\Scripts\python scripts\build_portable_full.py
.venv\Scripts\python scripts\package_release.py --suffix PJ-v3.3.10
```

Salida: `dist/AnonimizadorJudicial-NLP-PJ-v3.3.10.zip` — listo para
compartir.

Guía completa de empaquetado y entrega: [`docs/DEPLOY.md`](docs/DEPLOY.md).

---

## Arquitectura

- **FastAPI** en `127.0.0.1:8787` (sólo localhost)
- **Frontend** HTML / CSS / JS sin CDN (fuentes del sistema)
- **Detección por capas:**
  - Regex argentinos (DNI, CUIT, expedientes, patentes, domicilios…)
  - [Microsoft Presidio](https://microsoft.github.io/presidio/) + spaCy
    (`es_core_news_md`) para entidades nombradas
  - Catálogo externo `regex_limpio_v2.json` (extensible sin tocar código)
- **PDF:** pdfplumber (lectura) + ReportLab (export)
- **Resolución:** RapidFuzz + grafo (NetworkX) + panel de revisión humana
- **Exportación:** Word, PDF, CSV de equivalencias y **Markdown**
  (copiar al portapapeles para llevarlo a un asistente de IA)

## Funcionalidades

- Carga drag-and-drop de `.docx` o PDF digital (texto seleccionable).
- Detección automática de personas, DNI, CUIT/CUIL, empresas, emails,
  teléfonos, domicilios, patentes, expedientes y organismos.
- Tres modos de etiquetado: **categorizado** (`[PERSONA_1]`),
  **genérico** (`[NOMBRE]`) o **iniciales** (`J.P.G.`).
- Tabla de revisión: cambiar tipo, editar sustitución, unir variantes
  similares en un mismo grupo.
- Vista previa con resaltado de detecciones; selección manual para
  agregar lo que no se detectó.
- Editor final para retocar texto y formato antes de exportar.
- Exportación a Word, PDF, CSV de equivalencias y Markdown.

## Privacidad y seguridad

- El procesamiento ocurre **íntegramente en localhost** (`127.0.0.1:8787`).
- No hay llamadas a APIs en la nube, ni telemetría, ni CDNs en runtime.
- Presidio se configura **offline** (sin descargar la Public Suffix List).
- Los documentos cargados se guardan en una SQLite local
  (`data/sessions.db`) **que no se distribuye**.

Política de divulgación responsable: [SECURITY.md](SECURITY.md).

---

## Contribuir

Toda contribución es bienvenida. Antes de mandar un PR leé:

- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, tests, estilo, áreas
  donde necesitamos ayuda.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor Covenant.

Para reportar un bug usá la plantilla en `Issues → New issue → Reporte
de bug`. **No incluyas datos personales reales** ni en issues ni en
tests.

## Licencia y marcas

- **Código de la aplicación:** Apache 2.0 (ver [LICENSE](LICENSE)).
- **Componentes de terceros:** [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)
  y [LICENSES/](LICENSES/).
- **Modelo spaCy `es_core_news_md`:** GPL-3.0; se incluye sólo en el
  paquete portable, no en el código fuente.
- **Logo y nombre IALAB:** marcas institucionales, **no cubiertas** por
  la licencia Apache 2.0. Forks deben reemplazarlos antes de
  redistribuir. Ver [NOTICE](NOTICE).
- **Informe ejecutivo de cumplimiento:** [docs/COMPLIANCE.md](docs/COMPLIANCE.md).

---

Desarrollado por **IALAB** — Laboratorio de Innovación e Inteligencia
Artificial, Facultad de Derecho, Universidad de Buenos Aires.
