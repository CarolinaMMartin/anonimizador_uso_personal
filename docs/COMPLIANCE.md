# Cumplimiento legal y de licencias — Anonimizador Judicial

Versión de referencia: ver `app_version` en `/health`.

---

## 1. Resumen ejecutivo

| Aspecto | Estado en build estándar |
|---------|--------------------------|
| Procesamiento de datos | 100 % local (`127.0.0.1`), sin APIs en la nube |
| Conexión a Internet en runtime | **No requerida** (UI sin CDN; Presidio sin tldextract/red) |
| Datos personales en el ZIP | **No** (sin `sessions.db` ni documentos de ejemplo) |
| Componentes copyleft | **Modelo spaCy (GPL-3.0)** |
| PDF | **pdfplumber (MIT) + ReportLab (BSD)** |
| Licencias de terceros | `THIRD_PARTY_NOTICES.txt` + carpeta `LICENSES/` |

**Titularidad:** confirmar con IALAB/UBA (ver `LICENSE` en la raíz).

---

## 2. Tabla de cumplimiento por componente

| Componente / licencia | Qué requiere | Qué hacemos | Dónde queda |
|----------------------|--------------|-------------|-------------|
| **MIT / BSD / Apache** | Conservar aviso de licencia | `LICENSES/` + `THIRD_PARTY_NOTICES.txt` | Raíz + ZIP portable |
| **FastAPI, Presidio, spaCy lib., NetworkX, RapidFuzz, python-docx, pdfplumber, reportlab, Uvicorn, Pydantic** | Aviso permisivo | Listados como terceros | Informe + portable |
| **Modelo `es_core_news_md` (GPL-3.0)** | Aviso GPL al redistribuir binario + modelo | `LICENSES/GPL-3.0.txt` | Portable + docs |
| **PyInstaller** | Herramienta de build | Solo desarrollo | `THIRD_PARTY_NOTICES.txt` |
| **Diccionarios JSON propios** | Documentar autoría | `data/README.md` | Repo + ZIP |
| **Logo / marca IALAB** | Autorización institucional | Pendiente IALAB | Manual |
| **Fuentes** | Sin CDN | Fuentes del sistema | `frontend/styles.css` |
| **SQLite / sessions.db** | Privacidad | No se distribuye | Manual §7 |
| **Frontend propio** | Titularidad | `LICENSE` | Repo |

---

## 3. Modelo spaCy GPL-3.0

El portable incluye `models/es_core_news_md/` (~40 MB). Licencia **GPL-3.0**.

Texto completo incluido en el paquete: **`models/es_core_news_md/LICENSE`** (no editar).
Copia de referencia adicional: `LICENSES/GPL-3.0.txt`.

---

## 4. Componentes runtime del paquete Poder Judicial

- Motor: FastAPI + Uvicorn (localhost)
- Detección: **regex AR + Presidio + spaCy**
- Extracción PDF: **pdfplumber** (MIT)
- Export: **python-docx** (MIT), **ReportLab** (BSD)
- Resolución: RapidFuzz, NetworkX
- UI: HTML/CSS/JS propio
- Diccionarios + modelo spaCy

No hay OCR, LLM local, ni APIs externas de IA.

### Presidio y red (tldextract) — RESUELTO

Por defecto, el `EmailRecognizer` de Presidio usa `tldextract`, que en su
primera invocación intenta descargar la Public Suffix List desde
`publicsuffix.org` ([Presidio #1205](https://github.com/microsoft/presidio/issues/1205)).
Esto rompía la promesa de "procesamiento 100 % local" en redes aisladas.

**Mitigación aplicada desde v3.3.9 (vigente):**
- `EmailRecognizer` **removido** del analyzer Presidio.
- Emails detectados por **regex AR** + catálogo (`RGX_EMAIL`).
- `tldextract` forzado a usar un snapshot local embebido
  (`app/detection/presidio_offline.py`) que bloquea cualquier llamada a
  red.
- Test de regresión: `tests/test_presidio_offline.py` verifica que ni
  `tldextract` ni `presidio_analyzer` intenten resolver `publicsuffix.org`.

Se conserva esta nota como **decisión de diseño documentada**: si alguien
en un fork reactiva el `EmailRecognizer`, debe revisar también
`presidio_offline.py` para no reintroducir la fuga de red.

---

## 5. Checklist pre-despliegue (IT)

- [ ] Titularidad del código confirmada (UBA/IALAB)
- [ ] Autorización logo IALAB
- [ ] Puerto 8787 solo localhost
- [ ] `/health`: `presidio` y `spacy` en `true`
- [ ] Entregar: `THIRD_PARTY_NOTICES.txt`, `LICENSES/`, manuales
- [ ] Prueba en red aislada (sin Internet)

## 5 bis. Checklist pre-publicación open source

Antes de hacer público el repositorio en GitHub (o equivalente) verificar:

- [ ] `data/sessions.db` **NO** está versionado (`.gitignore` lo cubre).
- [ ] No hay logs de build (`build_ocr.log`, `build_output.log`,
      `*.log`) ni dumps de entorno (`dependencias.txt`, `pip-freeze*.txt`,
      `tree-proyecto.txt`) en el árbol.
- [ ] La carpeta `_archivo/` con artefactos legacy / dist obsoleto
      está borrada.
- [ ] `LICENSE` (Apache 2.0) y `NOTICE` (trademark IALAB) presentes en
      la raíz.
- [ ] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y `SECURITY.md` presentes
      con el email institucional.
- [ ] Plantillas `.github/ISSUE_TEMPLATE/` y `.github/PULL_REQUEST_TEMPLATE.md`
      activas.
- [ ] Workflow CI `.github/workflows/tests.yml` corre sobre la rama
      principal.
- [ ] `tests/` sólo contiene datos sintéticos: DNIs ficticios,
      `@example.invalid`, `@ejemplo.com.ar`, nombres genéricos.
- [ ] `frontend/logo-ialab.*` se mantiene **sólo** si el forker tiene
      autorización de IALAB. Caso contrario, reemplazar antes de publicar.
- [ ] `THIRD_PARTY_NOTICES.txt` refleja la lista actual de dependencias
      (sincronizar después de cualquier `pip install`).

---

## 6. Generación del paquete *(solo desarrollo; no aplica al usuario final)*

El usuario final **no ejecuta** estos comandos. Recibe el ZIP ya empaquetado.

```powershell
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\build_portable_full.py
.venv\Scripts\python scripts\package_release.py --suffix PJ-v3.3.10
```

---

*Última revisión: junio 2026*
